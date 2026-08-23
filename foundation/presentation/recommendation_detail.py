"""REC-UI-1 exact domain-native recommendation detail over the active presentation."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from typing import Callable, Mapping

from fastapi import FastAPI, Header, Query
from fastapi.responses import JSONResponse

from foundation.production.security import APIKeyAuthenticator, Permission


_STATUS_FIELDS = (
    "native_purchase_status",
    "native_recommendation",
    "recommendation",
)


@dataclass(frozen=True)
class RecommendationDetailRepository:
    connection_factory: Callable[[], object]

    @classmethod
    def from_dsn(cls, dsn: str) -> "RecommendationDetailRepository":
        if not dsn.strip():
            raise ValueError("PostgreSQL DSN must not be blank")
        import psycopg
        return cls(lambda: psycopg.connect(dsn))

    def detail(self, *, domain_id: str, asset_id: str) -> dict[str, object]:
        domain = domain_id.strip().lower()
        asset = asset_id.strip()
        if not domain:
            raise ValueError("domain must not be blank")
        if not asset:
            raise ValueError("asset_id must not be blank")

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
                SELECT r.record_key, r.payload_json, a.payload_json
                FROM presentation_records r
                JOIN presentation_records a
                  ON a.publication_id=r.publication_id
                 AND a.domain_id=r.domain_id
                 AND a.asset_id=r.asset_id
                 AND a.record_type='asset'
                WHERE r.publication_id=%s
                  AND r.record_type='recommendation'
                  AND r.domain_id=%s
                  AND r.asset_id=%s
                ORDER BY r.record_key
                """,
                (publication_id, domain, asset),
            )
            rows = cursor.fetchall()
            if len(rows) != 1:
                if not rows:
                    raise LookupError(
                        f"Recommendation '{asset}' is not present for domain '{domain}' in active presentation"
                    )
                raise RuntimeError(
                    f"Recommendation identity '{domain}/{asset}' is ambiguous in active presentation"
                )

            record_key, recommendation_payload, asset_payload = rows[0]

            cursor.execute(
                """
                SELECT record_key, payload_json
                FROM presentation_records
                WHERE publication_id=%s
                  AND domain_id=%s
                  AND asset_id=%s
                  AND record_type='forecast'
                ORDER BY record_key
                """,
                (publication_id, domain, asset),
            )
            forecast_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT record_key, payload_json
                FROM presentation_records
                WHERE publication_id=%s
                  AND domain_id=%s
                  AND asset_id=%s
                  AND record_type='risk'
                ORDER BY record_key
                """,
                (publication_id, domain, asset),
            )
            risk_rows = cursor.fetchall()

        recommendation = dict(recommendation_payload)
        asset_record = dict(asset_payload)
        status_source = None
        native_status = None
        for candidate in _STATUS_FIELDS:
            value = recommendation.get(candidate)
            if value is not None:
                native_status = value
                status_source = candidate
                break

        return {
            "publication_id": publication_id,
            "domain_id": domain,
            "asset_id": asset,
            "record_key": str(record_key),
            "asset_name": asset_record.get("asset_name"),
            "asset_symbol": asset_record.get("asset_symbol"),
            "asset_subclass": asset_record.get("asset_subclass"),
            "current_price_usd": asset_record.get("current_price_usd"),
            "current_price_authority_available": bool(
                asset_record.get("current_price_authority_available", False)
            ),
            "native_status": native_status,
            "native_status_source_field": status_source,
            "confidence_score": recommendation.get("confidence_score"),
            "native_rank": recommendation.get("native_rank"),
            "native_rank_type": recommendation.get("native_rank_type"),
            "manual_execution_price_check_required": recommendation.get(
                "manual_execution_price_check_required"
            ),
            "automatic_purchase_execution": bool(
                recommendation.get("automatic_purchase_execution", False)
            ),
            "recommendation_payload": recommendation,
            "asset_payload": asset_record,
            "forecast_records": [
                {"record_key": str(key), "payload": dict(payload)}
                for key, payload in forecast_rows
            ],
            "risk_records": [
                {"record_key": str(key), "payload": dict(payload)}
                for key, payload in risk_rows
            ],
            "domain_native_semantics": True,
            "universal_cross_domain_rank": False,
            "rank_comparison_scope": "NATIVE_RANK_TYPE_ONLY",
            "missing_fields_policy": "PRESERVE_MISSING",
        }


def install_recommendation_detail_routes(
    app: FastAPI,
    credentials: Mapping[str, tuple[str, tuple[str, ...]]],
    repository: RecommendationDetailRepository,
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

    @app.get("/v1/presentation/recommendation-detail")
    def recommendation_detail(
        domain: str = Query(..., min_length=1),
        asset_id: str = Query(..., min_length=1, max_length=500),
        x_api_key: str | None = Header(default=None),
    ):
        denied = authorize(x_api_key)
        if denied:
            return denied
        try:
            return repository.detail(domain_id=domain, asset_id=asset_id)
        except ValueError as error:
            return JSONResponse(
                {"error": {"code": "INVALID_REQUEST", "message": str(error)}},
                status_code=400,
            )
        except LookupError as error:
            return JSONResponse(
                {"error": {"code": "RECOMMENDATION_NOT_IN_ACTIVE_PRESENTATION", "message": str(error)}},
                status_code=404,
            )
        except RuntimeError as error:
            return JSONResponse(
                {"error": {"code": "AMBIGUOUS_RECOMMENDATION_IDENTITY", "message": str(error)}},
                status_code=409,
            )
