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

    def etf_guild(self) -> dict[str, object] | None:
        """The ETF package in the active publication: package summary plus every fund without its
        price history (fetch one fund with etf_fund for that). None if the publication has none."""
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            publication_id = self._active_id(cursor)
            cursor.execute("""
                SELECT record_type, record_key,
                       CASE WHEN record_type='etf_fund' THEN payload_json - 'history_monthly' - 'history_daily' ELSE payload_json END
                FROM presentation_records
                WHERE publication_id=%s AND domain_id='etf' AND record_type IN ('etf_fund', 'etf_package')
                ORDER BY record_type, record_key
            """, (publication_id,))
            rows = cursor.fetchall()
        package = next((dict(payload) for kind, _, payload in rows if kind == "etf_package"), None)
        funds = [dict(payload) for kind, _, payload in rows if kind == "etf_fund"]
        if package is None and not funds:
            return None
        return {"package": package, "funds": funds}

    def housing(self) -> dict[str, object] | None:
        """The housing package in the active publication: package summary plus each market. None if absent."""
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            publication_id = self._active_id(cursor)
            cursor.execute("""
                SELECT record_type, record_key, payload_json FROM presentation_records
                WHERE publication_id=%s AND domain_id='housing' AND record_type IN ('housing_market', 'housing_package')
                ORDER BY record_type, record_key
            """, (publication_id,))
            rows = cursor.fetchall()
        package = next((dict(payload) for kind, _, payload in rows if kind == "housing_package"), None)
        markets = [dict(payload) for kind, _, payload in rows if kind == "housing_market"]
        if package is None and not markets:
            return None
        return {"package": package, "markets": markets}

    def macro(self) -> dict[str, object] | None:
        """The macro package in the active publication: the current RSI reading plus history. None if absent."""
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            publication_id = self._active_id(cursor)
            cursor.execute("""
                SELECT record_type, payload_json FROM presentation_records
                WHERE publication_id=%s AND domain_id='macro' AND record_type IN ('macro_reading', 'macro_package')
            """, (publication_id,))
            rows = cursor.fetchall()
        current = next((dict(p) for kind, p in rows if kind == "macro_reading"), None)
        package = next((dict(p) for kind, p in rows if kind == "macro_package"), None)
        if current is None and package is None:
            return None
        return {"current": current, "package": package}

    def package_status(self) -> dict[str, dict[str, object]]:
        """Small freshness summary of the ETF, housing and macro packages in the active publication."""
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            publication_id = self._active_id(cursor)
            cursor.execute("""
                SELECT domain_id,
                       payload_json->>'generated_at_utc', payload_json->>'package_id', payload_json->>'model_version',
                       payload_json->>'source_run_id', payload_json->>'latest_input_observation',
                       payload_json->'data_quality'->>'status', payload_json->>'fund_count', payload_json->>'market_count'
                FROM presentation_records
                WHERE publication_id=%s AND record_type IN ('etf_package', 'housing_package', 'macro_package')
            """, (publication_id,))
            rows = cursor.fetchall()
            cursor.execute("""
                SELECT COUNT(*) FILTER (WHERE payload_json->>'freshness_state' = 'CURRENT'), COUNT(*)
                FROM presentation_records
                WHERE publication_id=%s AND domain_id='etf' AND record_type='etf_fund'
            """, (publication_id,))
            current_funds, funds = cursor.fetchone() or (0, 0)
        out: dict[str, dict[str, object]] = {}
        for domain, generated, package_id, model, run, latest, quality, fund_count, market_count in rows:
            out[str(domain)] = {"generated_at_utc": generated, "package_id": package_id, "model_version": model,
                                "source_run_id": run, "latest_input_observation": latest, "data_quality": quality,
                                "fund_count": int(fund_count) if fund_count else None,
                                "market_count": int(market_count) if market_count else None}
        if "etf" in out:
            out["etf"].update(current_funds=int(current_funds or 0), funds=int(funds or 0))
        return out

    def etf_fund(self, symbol: str) -> dict[str, object] | None:
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            publication_id = self._active_id(cursor)
            cursor.execute("""
                SELECT payload_json FROM presentation_records
                WHERE publication_id=%s AND domain_id='etf' AND record_type='etf_fund' AND record_key=%s
            """, (publication_id, symbol.strip().upper()))
            row = cursor.fetchone()
        return None if row is None else dict(row[0])

    def etf_latest_prices(self) -> dict[str, dict[str, object]]:
        """Latest package close per ETF ticker, for marking manual holdings. Empty when unavailable."""
        try:
            with closing(self.connection_factory()) as db, db.cursor() as cursor:
                publication_id = self._active_id(cursor)
                cursor.execute("""
                    SELECT COALESCE(payload_json->>'symbol', payload_json->>'ticker'), payload_json->>'close', payload_json->>'as_of_date',
                           payload_json->>'quality_status', payload_json->>'freshness_state',
                           payload_json->'_lineage'->>'package_id'
                    FROM presentation_records
                    WHERE publication_id=%s AND domain_id='etf' AND record_type='etf_fund'
                """, (publication_id,))
                rows = cursor.fetchall()
        except Exception:
            return {}
        out: dict[str, dict[str, object]] = {}
        for ticker, close, as_of, quality, freshness, package_id in rows:
            if not ticker or close in (None, "") or quality not in ("PASS", "PROVISIONAL"):
                continue
            out[str(ticker).upper()] = {"close": close, "as_of_date": as_of, "quality_status": quality,
                                        "freshness_state": freshness, "package_id": package_id}
        return out

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
        native_authority_records = records.get(
            "native_authority",
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
        premium_research_records = records.get(
            "mtg_premium_research",
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
        native_authorities = payloads(
            native_authority_records
        )
        forecasts = payloads(forecast_records)
        risks = payloads(risk_records)
        premium_research_payloads = payloads(
            premium_research_records
        )

        if len(premium_research_payloads) > 1:
            raise ValueError(
                "MTG premium projection refuses duplicate "
                "premium research authority"
            )

        premium_research = (
            premium_research_payloads[0]
            if premium_research_payloads
            else None
        )

        if premium_research is not None:
            for forbidden_field in (
                "automatic_purchase_execution",
                "execution_ready_purchase_certified",
            ):
                if forbidden_field in premium_research:
                    raise ValueError(
                        "MTG premium projection refuses "
                        "execution authority surface in "
                        f"{forbidden_field}"
                    )

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

        if native_authorities:
            native_authority = native_authorities[0]

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

        def strict_boolean(
            value: object,
            *,
            field_name: str,
        ) -> bool:
            if value is None:
                return False

            if isinstance(value, bool):
                return value

            if (
                isinstance(value, int)
                and not isinstance(value, bool)
                and value in (0, 1)
            ):
                return bool(value)

            if isinstance(value, str):
                normalized = value.strip().lower()

                if normalized in {
                    "true",
                    "yes",
                    "y",
                    "1",
                }:
                    return True

                if normalized in {
                    "false",
                    "no",
                    "n",
                    "0",
                    "",
                }:
                    return False

            raise ValueError(
                "Unsupported MTG boolean authority value "
                f"for {field_name}: {value!r}"
            )

        execution_ready = strict_boolean(
            native_authority.get(
                "execution_ready_purchase_certified"
            ),
            field_name=(
                "execution_ready_purchase_certified"
            ),
        )

        automatic_execution = strict_boolean(
            native_authority.get(
                "automatic_purchase_execution"
            ),
            field_name=(
                "automatic_purchase_execution"
            ),
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
                "native_authority_record_count": len(
                    native_authorities
                ),
                "recommendation_record_count": len(
                    recommendations
                ),
                "forecast_record_count": len(
                    forecasts
                ),
                "risk_record_count": len(
                    risks
                ),
                "premium_research_record_count": len(
                    premium_research_payloads
                ),
                "native_rank_state": rank_state,
                "native_purchase_state": purchase_state,
            },
            "forecasts": forecasts,
            "risk_metrics": risks,
            "premium_research": premium_research,
            "recommendations": recommendations,
            "native_authorities": native_authorities,
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

    @app.get("/v1/presentation/etf")
    def presentation_etf(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key)
        if denied:
            return denied
        try:
            guild = repository.etf_guild()
        except LookupError:
            guild = None
        if guild is None:
            return {"available": False, "package": None, "funds": []}
        return {"available": True, **guild}

    @app.get("/v1/presentation/housing")
    def presentation_housing(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key)
        if denied:
            return denied
        try:
            housing = repository.housing()
        except LookupError:
            housing = None
        if housing is None:
            return {"available": False, "package": None, "markets": []}
        return {"available": True, **housing}

    @app.get("/v1/presentation/macro")
    def presentation_macro(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key)
        if denied:
            return denied
        try:
            macro = repository.macro()
        except LookupError:
            macro = None
        if macro is None:
            return {"available": False, "current": None, "package": None}
        return {"available": True, **macro}

    @app.get("/v1/presentation/package-status")
    def presentation_package_status(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key)
        if denied:
            return denied
        try:
            packages = repository.package_status()
        except LookupError:
            packages = {}
        return {"packages": packages}

    @app.get("/v1/presentation/etf/{symbol}")
    def presentation_etf_fund(symbol: str, x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key)
        if denied:
            return denied
        if not symbol.replace(".", "").replace("-", "").isalnum() or len(symbol) > 12:
            return JSONResponse({"error": {"code": "INVALID_SYMBOL", "message": "symbol is not valid"}}, status_code=400)
        try:
            fund = repository.etf_fund(symbol)
        except LookupError:
            fund = None
        if fund is None:
            return JSONResponse({"error": {"code": "ETF_NOT_FOUND", "message": "fund is not in the active ETF package"}}, status_code=404)
        return fund

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
