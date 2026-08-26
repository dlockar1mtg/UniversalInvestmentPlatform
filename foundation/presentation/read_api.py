"""Authenticated read API over the active UIP presentation publication."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from typing import Callable, Mapping

from fastapi import FastAPI, Header, Query
from fastapi.responses import JSONResponse

from foundation.production.security import APIKeyAuthenticator, Permission


@dataclass(frozen=True)
class PresentationReadRepository:
    connection_factory: Callable[[], object]

    @classmethod
    def from_dsn(cls, dsn: str) -> "PresentationReadRepository":
        if not dsn.strip():
            raise ValueError("PostgreSQL DSN must not be blank")
        import psycopg
        return cls(lambda: psycopg.connect(dsn))

    def readiness(self) -> bool:
        try:
            return self.active_metadata() is not None
        except Exception:
            return False

    def active_metadata(self) -> dict[str, object] | None:
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            cursor.execute("""
                SELECT p.publication_id, p.publication_version,
                       p.source_database_sha256, p.source_database_classification,
                       p.published_at_utc, p.publication_status,
                       p.content_fingerprint, p.record_count,
                       a.activated_at_utc
                FROM presentation_active_publication a
                JOIN presentation_publications p USING (publication_id)
                WHERE a.singleton_id=1
            """)
            row = cursor.fetchone()
        if row is None:
            return None
        keys = (
            "publication_id", "publication_version", "source_database_sha256",
            "source_database_classification", "published_at_utc", "publication_status",
            "content_fingerprint", "record_count", "activated_at_utc",
        )
        return dict(zip(keys, row))

    def _active_id(self, cursor) -> str:
        cursor.execute("SELECT publication_id FROM presentation_active_publication WHERE singleton_id=1")
        row = cursor.fetchone()
        if row is None:
            raise LookupError("No active presentation publication")
        return str(row[0])

    def domain_health(self) -> tuple[dict[str, object], ...]:
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            publication_id = self._active_id(cursor)
            cursor.execute("""
                SELECT domain_id, payload_json
                FROM presentation_records
                WHERE publication_id=%s AND record_type='domain_health'
                ORDER BY domain_id
            """, (publication_id,))
            rows = cursor.fetchall()
        return tuple({"domain_id": str(domain), **dict(payload)} for domain, payload in rows)

    def recommendations(self, *, domain_id: str | None, limit: int, offset: int) -> tuple[dict[str, object], ...]:
        parameters: list[object] = []
        where = ["r.publication_id=a.publication_id", "a.singleton_id=1", "r.record_type='recommendation'"]
        if domain_id is not None:
            where.append("r.domain_id=%s")
            parameters.append(domain_id)
        parameters.extend([limit, offset])
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT r.domain_id, r.asset_id, r.record_key, r.payload_json
                FROM presentation_records r
                JOIN presentation_active_publication a ON TRUE
                WHERE {' AND '.join(where)}
                ORDER BY r.domain_id, r.record_key
                LIMIT %s OFFSET %s
                """,
                parameters,
            )
            rows = cursor.fetchall()
        return tuple({
            "domain_id": str(domain),
            "asset_id": None if asset_id is None else str(asset_id),
            "record_key": str(record_key),
            "payload": dict(payload),
        } for domain, asset_id, record_key, payload in rows)

    def recommendation_catalog(self, *, domain_id: str | None, limit: int, offset: int) -> tuple[dict[str, object], ...]:
        parameters: list[object] = []
        where = ["r.publication_id=a.publication_id", "a.singleton_id=1", "r.record_type='recommendation'"]
        if domain_id is not None:
            where.append("r.domain_id=%s")
            parameters.append(domain_id)
        parameters.extend([limit, offset])
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT r.domain_id, r.asset_id, r.record_key, r.payload_json,
                       (
                           SELECT ar.payload_json
                           FROM presentation_records ar
                           WHERE ar.publication_id=r.publication_id
                             AND ar.domain_id=r.domain_id
                             AND ar.asset_id=r.asset_id
                             AND ar.record_type='asset'
                           ORDER BY ar.record_key
                           LIMIT 1
                       ) AS asset_payload_json
                FROM presentation_records r
                JOIN presentation_active_publication a ON TRUE
                WHERE {' AND '.join(where)}
                ORDER BY r.domain_id, r.record_key
                LIMIT %s OFFSET %s
                """,
                parameters,
            )
            rows = cursor.fetchall()

        items: list[dict[str, object]] = []
        for domain, asset_id, record_key, payload, asset_payload in rows:
            identity = {} if asset_payload is None else dict(asset_payload)
            canonical_asset_id = None if asset_id is None else str(asset_id)
            display_name = (
                identity.get("asset_name")
                or identity.get("product_name")
                or identity.get("name")
                or canonical_asset_id
            )
            symbol = identity.get("asset_symbol") or identity.get("symbol")
            subclass = (
                identity.get("asset_subclass")
                or identity.get("lane")
                or identity.get("mtg_lane")
            )
            items.append({
                "domain_id": str(domain),
                "asset_id": canonical_asset_id,
                "record_key": str(record_key),
                "asset_name": None if display_name is None else str(display_name),
                "asset_symbol": None if symbol is None else str(symbol),
                "asset_subclass": None if subclass is None else str(subclass),
                "payload": dict(payload),
            })
        return tuple(items)

    def asset_detail(self, domain_id: str, asset_id: str) -> dict[str, object] | None:
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            publication_id = self._active_id(cursor)
            cursor.execute("""
                SELECT record_type, record_key, payload_json
                FROM presentation_records
                WHERE publication_id=%s AND domain_id=%s AND asset_id=%s
                ORDER BY record_type, record_key
            """, (publication_id, domain_id, asset_id))
            rows = cursor.fetchall()
        if not rows:
            return None
        grouped: dict[str, list[dict[str, object]]] = {}
        for record_type, record_key, payload in rows:
            grouped.setdefault(str(record_type), []).append({
                "record_key": str(record_key),
                "payload": dict(payload),
            })
        return {"domain_id": domain_id, "asset_id": asset_id, "records": grouped}

    def mtg_premium_research(
        self,
        asset_id: str,
    ) -> dict[str, object] | None:
        """Project lane-native MTG premium research from active publication records.

        This method does not invent missing authority and does not create a
        universal MTG rank. It only projects fields already present in the
        active certified presentation publication.
        """
        detail = self.asset_detail("mtg", asset_id)

        if detail is None:
            return None

        records = detail["records"]

        asset_records = records.get("asset", [])
        recommendation_records = records.get(
            "recommendation",
            [],
        )
        forecast_records = records.get(
            "forecast",
            [],
        )
        risk_records = records.get(
            "risk_metric",
            [],
        )

        def payloads(items):
            return [
                dict(item["payload"])
                for item in items
            ]

        assets = payloads(asset_records)
        recommendations = payloads(
            recommendation_records
        )
        forecasts = payloads(forecast_records)
        risks = payloads(risk_records)

        identity: dict[str, object] = {}

        if assets:
            identity = assets[0]

        lane = str(
            identity.get("mtg_lane")
            or identity.get("lane")
            or identity.get("asset_subclass")
            or ""
        ).strip()

        lane_upper = lane.upper()

        native_authority: dict[str, object] = {}

        if recommendations:
            native_authority = recommendations[0]

        native_rank = native_authority.get(
            "native_rank"
        )
        native_rank_type = native_authority.get(
            "native_rank_type"
        )
        native_purchase_status = (
            native_authority.get(
                "native_purchase_status"
            )
        )
        purchase_semantic = (
            native_authority.get(
                "purchase_semantic"
            )
        )

        execution_ready = bool(
            native_authority.get(
                "execution_ready_purchase_certified",
                False,
            )
        )

        automatic_execution = bool(
            native_authority.get(
                "automatic_purchase_execution",
                False,
            )
        )

        if automatic_execution:
            raise ValueError(
                "MTG premium projection refuses automatic "
                "purchase execution authority"
            )

        presentation_state = (
            "NATIVE_CORE_ONLY"
        )

        research_state = (
            "PARTIAL"
        )

        rank_state = (
            "AVAILABLE"
            if native_rank is not None
            else "MISSING"
        )

        purchase_state = (
            "AVAILABLE"
            if native_purchase_status
            else "MISSING"
        )

        if "SECRET" in lane_upper:
            presentation_state = (
                "SECRET_LAIR_PREMIUM_RESEARCH"
            )

            if (
                forecasts
                and risks
                and native_rank is not None
                and native_purchase_status
            ):
                research_state = "FULL"
            else:
                research_state = "PARTIAL"

        elif (
            "PRE" in lane_upper
            and "COLLECTOR" in lane_upper
        ):
            presentation_state = (
                "PRECOLLECTOR_CERTIFICATION_BRIDGE_REQUIRED"
            )
            research_state = "BLOCKED"

        elif "COLLECTOR" in lane_upper:
            presentation_state = (
                "COLLECTOR_CERTIFIED_CORE"
            )
            research_state = "PARTIAL"

        result = {
            "domain_id": "mtg",
            "asset_id": asset_id,
            "lane": lane or None,
            "presentation_state": presentation_state,
            "research_state": research_state,
            "identity": identity,
            "native_authority": {
                "native_rank": native_rank,
                "native_rank_type": native_rank_type,
                "native_purchase_status": (
                    native_purchase_status
                ),
                "purchase_semantic": purchase_semantic,
                "evidence_state": (
                    native_authority.get(
                        "evidence_state"
                    )
                ),
                "actionability_state": (
                    native_authority.get(
                        "actionability_state"
                    )
                ),
                "manual_execution_price_check_required": (
                    native_authority.get(
                        "manual_execution_price_check_required"
                    )
                ),
                "execution_ready_purchase_certified": (
                    execution_ready
                ),
                "automatic_purchase_execution": False,
            },
            "authority_availability": {
                "forecast_record_count": len(
                    forecasts
                ),
                "risk_record_count": len(
                    risks
                ),
                "native_rank_state": rank_state,
                "native_purchase_state": purchase_state,
            },
            "forecasts": forecasts,
            "risk_metrics": risks,
            "recommendations": recommendations,
            "presentation_semantics": {
                "cross_domain_rank_created": False,
                "universal_mtg_rank_created": False,
                "native_purchase_semantics_preserved": True,
                "missing_authority_remains_missing": True,
                "automatic_purchase_execution_authorized": False,
            },
        }

        if presentation_state == (
            "PRECOLLECTOR_CERTIFICATION_BRIDGE_REQUIRED"
        ):
            result["blocked_reason"] = (
                "Pre-Collector premium scenario promotion "
                "requires a certified presentation authority."
            )

        if (
            presentation_state
            == "COLLECTOR_CERTIFIED_CORE"
        ):
            result["ranking_bridge_state"] = (
                "IDENTITY_BRIDGE_REQUIRED"
            )

        if (
            presentation_state
            == "SECRET_LAIR_PREMIUM_RESEARCH"
            and research_state == "PARTIAL"
        ):
            result["missing_research_label"] = (
                "Native premium research is incomplete "
                "for this product."
            )

        return result


    def lineage(self, domain_id: str, asset_id: str) -> dict[str, object] | None:
        detail = self.asset_detail(domain_id, asset_id)
        if detail is None:
            return None
        lineage_keys = (
            "run_id", "_import_id", "_package_id", "_manifest_sha256", "_imported_at_utc",
            "native_authority_pointer", "native_authority_sha256", "source_system", "model_version",
        )
        items: list[dict[str, object]] = []
        for record_type, records in detail["records"].items():
            for record in records:
                payload = record["payload"]
                evidence = {key: payload.get(key) for key in lineage_keys if key in payload}
                if evidence:
                    items.append({"record_type": record_type, "record_key": record["record_key"], "lineage": evidence})
        return {"domain_id": domain_id, "asset_id": asset_id, "items": items}


def install_presentation_read_routes(
    app: FastAPI,
    credentials: Mapping[str, tuple[str, tuple[str, ...]]],
    repository: PresentationReadRepository,
) -> None:
    """Install authenticated read-only endpoints for the active presentation version."""
    principals, hashes = {}, {}
    for principal_id, (credential, roles) in sorted(credentials.items()):
        principals[principal_id] = roles
        hashes[principal_id] = APIKeyAuthenticator.hash_credential(credential)
    authenticator = APIKeyAuthenticator(principals, hashes)

    def authorize(credential: str | None):
        principal = authenticator.authenticate(credential)
        if principal is None:
            return JSONResponse({"error": {"code": "UNAUTHENTICATED", "message": "valid credentials are required"}}, status_code=401)
        if not principal.permits(Permission.RUN_READ):
            return JSONResponse({"error": {"code": "FORBIDDEN", "message": "read permission is required"}}, status_code=403)
        return None

    def normalize_domain(domain: str | None):
        normalized = None if domain is None else domain.strip().lower()
        if normalized is not None and normalized not in {"crypto", "metals", "mtg"}:
            return None, JSONResponse({"error": {"code": "INVALID_DOMAIN", "message": "domain must be crypto, metals, or mtg"}}, status_code=400)
        return normalized, None

    @app.get("/v1/presentation/status")
    def presentation_status(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key)
        if denied:
            return denied
        metadata = repository.active_metadata()
        if metadata is None:
            return JSONResponse({"error": {"code": "NO_ACTIVE_PRESENTATION", "message": "no active certified presentation publication"}}, status_code=503)
        return metadata

    @app.get("/v1/presentation/domain-health")
    def presentation_domain_health(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key)
        return denied or {"items": repository.domain_health()}

    @app.get("/v1/presentation/recommendations")
    def presentation_recommendations(
        domain: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        x_api_key: str | None = Header(default=None),
    ):
        denied = authorize(x_api_key)
        if denied:
            return denied
        normalized, invalid = normalize_domain(domain)
        if invalid:
            return invalid
        return {"items": repository.recommendations(domain_id=normalized, limit=limit, offset=offset), "limit": limit, "offset": offset}

    @app.get("/v1/presentation/recommendation-catalog")
    def presentation_recommendation_catalog(
        domain: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        x_api_key: str | None = Header(default=None),
    ):
        denied = authorize(x_api_key)
        if denied:
            return denied
        normalized, invalid = normalize_domain(domain)
        if invalid:
            return invalid
        return {"items": repository.recommendation_catalog(domain_id=normalized, limit=limit, offset=offset), "limit": limit, "offset": offset}

    @app.get("/v1/presentation/assets/{domain_id}/{asset_id}")
    def presentation_asset(domain_id: str, asset_id: str, x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key)
        if denied:
            return denied
        detail = repository.asset_detail(domain_id.strip().lower(), asset_id)
        if detail is None:
            return JSONResponse({"error": {"code": "ASSET_NOT_FOUND", "message": "asset is not present in the active presentation publication"}}, status_code=404)
        return detail

    @app.get("/v1/presentation/mtg-research/{asset_id}")
    def presentation_mtg_research(
        asset_id: str,
        x_api_key: str | None = Header(default=None),
    ):
        denied = authorize(x_api_key)

        if denied:
            return denied

        detail = repository.mtg_premium_research(
            asset_id
        )

        if detail is None:
            return JSONResponse(
                {
                    "error": {
                        "code": "ASSET_NOT_FOUND",
                        "message": (
                            "MTG asset is not present in "
                            "the active presentation publication"
                        ),
                    }
                },
                status_code=404,
            )

        return detail


    @app.get("/v1/presentation/lineage/{domain_id}/{asset_id}")
    def presentation_lineage(domain_id: str, asset_id: str, x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key)
        if denied:
            return denied
        lineage = repository.lineage(domain_id.strip().lower(), asset_id)
        if lineage is None:
            return JSONResponse({"error": {"code": "ASSET_NOT_FOUND", "message": "asset is not present in the active presentation publication"}}, status_code=404)
        return lineage
