"""REC-UI-1 domain-native recommendation summary over the active presentation."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from typing import Callable, Mapping

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

from foundation.production.security import APIKeyAuthenticator, Permission


@dataclass(frozen=True)
class RecommendationSummaryRepository:
    connection_factory: Callable[[], object]

    @classmethod
    def from_dsn(cls, dsn: str) -> "RecommendationSummaryRepository":
        if not dsn.strip():
            raise ValueError("PostgreSQL DSN must not be blank")
        import psycopg
        return cls(lambda: psycopg.connect(dsn))

    def summary(self) -> dict[str, object]:
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT publication_id FROM presentation_active_publication WHERE singleton_id=1"
            )
            active = cursor.fetchone()
            if active is None:
                raise LookupError("No active presentation publication")
            publication_id = str(active[0])

            cursor.execute(
                """
                SELECT
                    r.domain_id,
                    COUNT(*) AS recommendation_count,
                    COUNT(*) FILTER (
                        WHERE COALESCE(
                            r.payload_json->>'native_purchase_status',
                            r.payload_json->>'native_recommendation',
                            r.payload_json->>'recommendation'
                        ) IS NOT NULL
                    ) AS native_status_count,
                    COUNT(*) FILTER (
                        WHERE r.payload_json->>'confidence_score' IS NOT NULL
                    ) AS confidence_count,
                    COUNT(*) FILTER (
                        WHERE r.payload_json->>'native_rank' IS NOT NULL
                    ) AS native_rank_count,
                    COUNT(*) FILTER (
                        WHERE r.payload_json->>'native_rank_type' IS NOT NULL
                    ) AS native_rank_type_count,
                    COUNT(*) FILTER (
                        WHERE (r.payload_json->>'manual_execution_price_check_required')::boolean IS TRUE
                    ) AS manual_price_check_count,
                    COUNT(*) FILTER (
                        WHERE (r.payload_json->>'automatic_purchase_execution')::boolean IS TRUE
                    ) AS automatic_execution_count,
                    COUNT(a.asset_id) AS matched_asset_count,
                    COUNT(*) FILTER (
                        WHERE (a.payload_json->>'current_price_authority_available')::boolean IS TRUE
                    ) AS certified_current_price_authority_count,
                    COUNT(DISTINCT f.asset_id) AS forecast_asset_count,
                    COUNT(DISTINCT k.asset_id) AS risk_asset_count
                FROM presentation_records r
                LEFT JOIN presentation_records a
                  ON a.publication_id=r.publication_id
                 AND a.domain_id=r.domain_id
                 AND a.asset_id=r.asset_id
                 AND a.record_type='asset'
                LEFT JOIN presentation_records f
                  ON f.publication_id=r.publication_id
                 AND f.domain_id=r.domain_id
                 AND f.asset_id=r.asset_id
                 AND f.record_type='forecast'
                LEFT JOIN presentation_records k
                  ON k.publication_id=r.publication_id
                 AND k.domain_id=r.domain_id
                 AND k.asset_id=r.asset_id
                 AND k.record_type='risk'
                WHERE r.publication_id=%s
                  AND r.record_type='recommendation'
                GROUP BY r.domain_id
                ORDER BY r.domain_id
                """,
                (publication_id,),
            )
            aggregate_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    domain_id,
                    COALESCE(
                        payload_json->>'native_purchase_status',
                        payload_json->>'native_recommendation',
                        payload_json->>'recommendation'
                    ) AS native_status,
                    COUNT(*)
                FROM presentation_records
                WHERE publication_id=%s
                  AND record_type='recommendation'
                GROUP BY domain_id, native_status
                ORDER BY domain_id, native_status
                """,
                (publication_id,),
            )
            status_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT domain_id, payload_json->>'native_rank_type', COUNT(*)
                FROM presentation_records
                WHERE publication_id=%s
                  AND record_type='recommendation'
                  AND payload_json->>'native_rank_type' IS NOT NULL
                GROUP BY domain_id, payload_json->>'native_rank_type'
                ORDER BY domain_id, payload_json->>'native_rank_type'
                """,
                (publication_id,),
            )
            rank_type_rows = cursor.fetchall()

        statuses: dict[str, dict[str, int]] = {}
        for domain_id, native_status, count in status_rows:
            if native_status is None:
                continue
            statuses.setdefault(str(domain_id), {})[str(native_status)] = int(count)

        rank_types: dict[str, dict[str, int]] = {}
        for domain_id, rank_type, count in rank_type_rows:
            rank_types.setdefault(str(domain_id), {})[str(rank_type)] = int(count)

        domains: list[dict[str, object]] = []
        automatic_execution_total = 0
        for row in aggregate_rows:
            (
                domain_id,
                recommendation_count,
                native_status_count,
                confidence_count,
                native_rank_count,
                native_rank_type_count,
                manual_price_check_count,
                automatic_execution_count,
                matched_asset_count,
                certified_current_price_authority_count,
                forecast_asset_count,
                risk_asset_count,
            ) = row
            domain = str(domain_id)
            automatic_execution_total += int(automatic_execution_count)
            domains.append(
                {
                    "domain_id": domain,
                    "recommendation_count": int(recommendation_count),
                    "native_status_count": int(native_status_count),
                    "native_statuses": statuses.get(domain, {}),
                    "confidence_count": int(confidence_count),
                    "native_rank_count": int(native_rank_count),
                    "native_rank_type_count": int(native_rank_type_count),
                    "native_rank_types": rank_types.get(domain, {}),
                    "manual_price_check_required_count": int(manual_price_check_count),
                    "automatic_execution_count": int(automatic_execution_count),
                    "matched_asset_count": int(matched_asset_count),
                    "certified_current_price_authority_count": int(
                        certified_current_price_authority_count
                    ),
                    "forecast_asset_count": int(forecast_asset_count),
                    "risk_asset_count": int(risk_asset_count),
                    "identity_coverage": f"{int(matched_asset_count)}/{int(recommendation_count)}",
                    "forecast_coverage": f"{int(forecast_asset_count)}/{int(recommendation_count)}",
                    "risk_coverage": f"{int(risk_asset_count)}/{int(recommendation_count)}",
                }
            )

        return {
            "publication_id": publication_id,
            "total_recommendations": sum(item["recommendation_count"] for item in domains),
            "domains": domains,
            "domain_native_semantics": True,
            "universal_cross_domain_rank": False,
            "automatic_execution": automatic_execution_total > 0,
            "missing_fields_policy": "PRESERVE_MISSING",
        }


def install_recommendation_summary_routes(
    app: FastAPI,
    credentials: Mapping[str, tuple[str, tuple[str, ...]]],
    repository: RecommendationSummaryRepository,
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

    @app.get("/v1/presentation/recommendation-summary")
    def recommendation_summary(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key)
        if denied:
            return denied
        try:
            return repository.summary()
        except LookupError as error:
            return JSONResponse(
                {"error": {"code": "NO_ACTIVE_PRESENTATION", "message": str(error)}},
                status_code=503,
            )
