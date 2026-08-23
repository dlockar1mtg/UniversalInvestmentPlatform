"""REC-UI-1 domain-native recommendation list over the active presentation."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from typing import Callable, Mapping

from fastapi import FastAPI, Header, Query
from fastapi.responses import JSONResponse

from foundation.production.security import APIKeyAuthenticator, Permission


@dataclass(frozen=True)
class RecommendationListRepository:
    connection_factory: Callable[[], object]

    @classmethod
    def from_dsn(cls, dsn: str) -> "RecommendationListRepository":
        if not dsn.strip():
            raise ValueError("PostgreSQL DSN must not be blank")
        import psycopg
        return cls(lambda: psycopg.connect(dsn))

    def list(
        self,
        *,
        domain_id: str,
        limit: int,
        offset: int,
        query: str | None = None,
    ) -> dict[str, object]:
        domain = domain_id.strip().lower()
        if not domain:
            raise ValueError("domain must not be blank")
        search = None if query is None else query.strip()
        if search == "":
            search = None

        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT publication_id FROM presentation_active_publication WHERE singleton_id=1"
            )
            active = cursor.fetchone()
            if active is None:
                raise LookupError("No active presentation publication")
            publication_id = str(active[0])

            filters = [
                "r.publication_id=%s",
                "r.record_type='recommendation'",
                "r.domain_id=%s",
            ]
            parameters: list[object] = [publication_id, domain]
            if search is not None:
                filters.append(
                    "(" 
                    "r.asset_id ILIKE %s OR "
                    "COALESCE(a.payload_json->>'asset_name','') ILIKE %s OR "
                    "COALESCE(a.payload_json->>'asset_symbol','') ILIKE %s"
                    ")"
                )
                pattern = f"%{search}%"
                parameters.extend([pattern, pattern, pattern])
            where_sql = " AND ".join(filters)

            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM presentation_records r
                JOIN presentation_records a
                  ON a.publication_id=r.publication_id
                 AND a.domain_id=r.domain_id
                 AND a.asset_id=r.asset_id
                 AND a.record_type='asset'
                WHERE {where_sql}
                """,
                parameters,
            )
            total = int(cursor.fetchone()[0])
            if total == 0 and search is None:
                raise LookupError(
                    f"No recommendations for domain '{domain}' in active presentation"
                )

            cursor.execute(
                f"""
                SELECT
                    r.asset_id,
                    r.record_key,
                    r.payload_json,
                    a.payload_json,
                    (
                        SELECT COUNT(*)
                        FROM presentation_records f
                        WHERE f.publication_id=r.publication_id
                          AND f.domain_id=r.domain_id
                          AND f.asset_id=r.asset_id
                          AND f.record_type='forecast'
                    ) AS forecast_record_count,
                    (
                        SELECT COUNT(*)
                        FROM presentation_records k
                        WHERE k.publication_id=r.publication_id
                          AND k.domain_id=r.domain_id
                          AND k.asset_id=r.asset_id
                          AND k.record_type='risk'
                    ) AS risk_record_count
                FROM presentation_records r
                JOIN presentation_records a
                  ON a.publication_id=r.publication_id
                 AND a.domain_id=r.domain_id
                 AND a.asset_id=r.asset_id
                 AND a.record_type='asset'
                WHERE {where_sql}
                ORDER BY
                    COALESCE(a.payload_json->>'asset_name', r.asset_id),
                    r.asset_id,
                    r.record_key
                LIMIT %s OFFSET %s
                """,
                [*parameters, limit, offset],
            )
            rows = cursor.fetchall()

        items: list[dict[str, object]] = []
        for (
            asset_id,
            record_key,
            recommendation_payload,
            asset_payload,
            forecast_record_count,
            risk_record_count,
        ) in rows:
            recommendation = dict(recommendation_payload)
            asset = dict(asset_payload)

            status_source = None
            native_status = None
            for candidate in (
                "native_purchase_status",
                "native_recommendation",
                "recommendation",
            ):
                value = recommendation.get(candidate)
                if value is not None:
                    native_status = value
                    status_source = candidate
                    break

            automatic_execution = bool(
                recommendation.get("automatic_purchase_execution", False)
            )
            items.append(
                {
                    "domain_id": domain,
                    "asset_id": str(asset_id),
                    "record_key": str(record_key),
                    "asset_name": asset.get("asset_name"),
                    "asset_symbol": asset.get("asset_symbol"),
                    "asset_subclass": asset.get("asset_subclass"),
                    "native_status": native_status,
                    "native_status_source_field": status_source,
                    "confidence_score": recommendation.get("confidence_score"),
                    "native_rank": recommendation.get("native_rank"),
                    "native_rank_type": recommendation.get("native_rank_type"),
                    "current_price_usd": asset.get("current_price_usd"),
                    "current_price_authority_available": bool(
                        asset.get("current_price_authority_available", False)
                    ),
                    "manual_execution_price_check_required": recommendation.get(
                        "manual_execution_price_check_required"
                    ),
                    "automatic_purchase_execution": automatic_execution,
                    "forecast_record_count": int(forecast_record_count),
                    "risk_record_count": int(risk_record_count),
                    "recommendation_payload": recommendation,
                }
            )

        return {
            "publication_id": publication_id,
            "domain_id": domain,
            "total": total,
            "limit": limit,
            "offset": offset,
            "query": search,
            "items": items,
            "domain_native_semantics": True,
            "universal_cross_domain_rank": False,
            "ordering_policy": "STABLE_ASSET_IDENTITY_NOT_NATIVE_RANK",
            "rank_comparison_scope": "NATIVE_RANK_TYPE_ONLY",
            "automatic_execution": any(
                bool(item["automatic_purchase_execution"]) for item in items
            ),
            "missing_fields_policy": "PRESERVE_MISSING",
        }


def install_recommendation_list_routes(
    app: FastAPI,
    credentials: Mapping[str, tuple[str, tuple[str, ...]]],
    repository: RecommendationListRepository,
) -> None:
    principals, hashes = {}, {}
    for principal_id, (credential, roles) in sorted(credentials.items()):
        principals[principal_id] = roles
        hashes[principal_id] = APIKeyAuthenticator.hash_credential(credential)
    authenticator = APIKeyAuthenticator(principals, hashes)

    def authorize(credential: str | None):
        principal = authenticator.authenticate(credential)
        if principal is None:
            return JSONResponse(
                {"error": {"code": "UNAUTHENTICATED", "message": "valid credentials are required"}},
                status_code=401,
            )
        if not principal.permits(Permission.RUN_READ):
            return JSONResponse(
                {"error": {"code": "FORBIDDEN", "message": "read permission is required"}},
                status_code=403,
            )
        return None

    @app.get("/v1/presentation/recommendation-list")
    def recommendation_list(
        domain: str = Query(..., min_length=1),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        query: str | None = Query(default=None, max_length=200),
        x_api_key: str | None = Header(default=None),
    ):
        denied = authorize(x_api_key)
        if denied:
            return denied
        try:
            return repository.list(
                domain_id=domain,
                limit=limit,
                offset=offset,
                query=query,
            )
        except ValueError as error:
            return JSONResponse(
                {"error": {"code": "INVALID_REQUEST", "message": str(error)}},
                status_code=400,
            )
        except LookupError as error:
            return JSONResponse(
                {"error": {"code": "DOMAIN_NOT_IN_ACTIVE_PRESENTATION", "message": str(error)}},
                status_code=404,
            )
