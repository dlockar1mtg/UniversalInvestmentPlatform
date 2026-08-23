"""Governed asset catalog over the active UIP presentation publication."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from typing import Callable, Mapping

from fastapi import FastAPI, Header, Query
from fastapi.responses import JSONResponse

from foundation.production.security import APIKeyAuthenticator, Permission


@dataclass(frozen=True)
class GovernedAssetCatalogRepository:
    """Read only domain and asset identities from the active publication."""

    connection_factory: Callable[[], object]

    @classmethod
    def from_dsn(cls, dsn: str) -> "GovernedAssetCatalogRepository":
        if not dsn.strip():
            raise ValueError("PostgreSQL DSN must not be blank")
        import psycopg
        return cls(lambda: psycopg.connect(dsn))

    def domains(self) -> tuple[str, ...]:
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT r.domain_id
                FROM presentation_records r
                JOIN presentation_active_publication a
                  ON a.publication_id=r.publication_id
                WHERE a.singleton_id=1
                  AND r.record_type='asset'
                ORDER BY r.domain_id
            """)
            rows = cursor.fetchall()
        return tuple(str(row[0]) for row in rows)

    def search_assets(
        self,
        *,
        domain_id: str,
        query: str = "",
        limit: int = 50,
    ) -> tuple[dict[str, object], ...]:
        domain = domain_id.strip().lower()
        term = query.strip()
        if not domain:
            raise ValueError("domain is required")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        pattern = f"%{term}%"
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            cursor.execute("""
                SELECT r.domain_id, r.asset_id, r.payload_json
                FROM presentation_records r
                JOIN presentation_active_publication a
                  ON a.publication_id=r.publication_id
                WHERE a.singleton_id=1
                  AND r.record_type='asset'
                  AND r.domain_id=%s
                  AND (
                        %s=''
                        OR r.asset_id ILIKE %s
                        OR COALESCE(r.payload_json->>'asset_name','') ILIKE %s
                        OR COALESCE(r.payload_json->>'asset_symbol','') ILIKE %s
                        OR COALESCE(r.payload_json->>'asset_subclass','') ILIKE %s
                  )
                ORDER BY
                  COALESCE(r.payload_json->>'asset_name',''),
                  COALESCE(r.payload_json->>'asset_symbol',''),
                  r.asset_id
                LIMIT %s
            """, (domain, term, pattern, pattern, pattern, pattern, limit))
            rows = cursor.fetchall()
        items: list[dict[str, object]] = []
        for row_domain, asset_id, payload in rows:
            document = dict(payload)
            items.append({
                "domain_id": str(row_domain),
                "asset_id": str(asset_id),
                "asset_name": document.get("asset_name") or str(asset_id),
                "asset_symbol": document.get("asset_symbol"),
                "asset_class": document.get("asset_class"),
                "asset_subclass": document.get("asset_subclass"),
            })
        return tuple(items)

    def asset_exists(self, domain_id: str, asset_id: str) -> bool:
        domain = domain_id.strip().lower()
        asset = asset_id.strip()
        if not domain or not asset:
            return False
        with closing(self.connection_factory()) as db, db.cursor() as cursor:
            cursor.execute("""
                SELECT 1
                FROM presentation_records r
                JOIN presentation_active_publication a
                  ON a.publication_id=r.publication_id
                WHERE a.singleton_id=1
                  AND r.record_type='asset'
                  AND r.domain_id=%s
                  AND r.asset_id=%s
                LIMIT 1
            """, (domain, asset))
            return cursor.fetchone() is not None


def install_governed_asset_catalog_routes(
    app: FastAPI,
    credentials: Mapping[str, tuple[str, tuple[str, ...]]],
    repository: GovernedAssetCatalogRepository,
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

    @app.get("/v1/presentation/domains")
    def governed_domains(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key)
        if denied:
            return denied
        return {"items": [{"domain_id": item} for item in repository.domains()]}

    @app.get("/v1/presentation/assets")
    def governed_assets(
        domain: str = Query(...),
        query: str = Query(default=""),
        limit: int = Query(default=50, ge=1, le=100),
        x_api_key: str | None = Header(default=None),
    ):
        denied = authorize(x_api_key)
        if denied:
            return denied
        normalized = domain.strip().lower()
        domains = repository.domains()
        if normalized not in domains:
            return JSONResponse(
                {"error": {"code": "INVALID_DOMAIN", "message": "domain is not present in the active certified asset catalog"}},
                status_code=400,
            )
        return {
            "items": repository.search_assets(domain_id=normalized, query=query, limit=limit),
            "domain": normalized,
            "query": query,
            "limit": limit,
        }
