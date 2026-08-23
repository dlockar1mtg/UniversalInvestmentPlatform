"""Hosted PORT-1 read API derived from the append-only transaction ledger."""

from __future__ import annotations

from typing import Mapping

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

from foundation.production.portfolio_accounting import derive_portfolio
from foundation.production.portfolio_enrichment import PresentationAssetReader, enrich_portfolio
from foundation.production.security import APIKeyAuthenticator, Permission
from foundation.production.transaction_persistence import TransactionRepository


def _authenticator(credentials: Mapping[str, tuple[str, tuple[str, ...]]]) -> APIKeyAuthenticator:
    principals, hashes = {}, {}
    for principal_id, (credential, roles) in sorted(credentials.items()):
        principals[principal_id] = roles
        hashes[principal_id] = APIKeyAuthenticator.hash_credential(credential)
    return APIKeyAuthenticator(principals, hashes)


def _authorize(authenticator: APIKeyAuthenticator, credential: str | None):
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


def _derive(transaction_repository: TransactionRepository):
    transactions = transaction_repository.list(limit=500, offset=0)
    return derive_portfolio(transactions)


def install_transaction_portfolio_routes(
    app: FastAPI,
    credentials: Mapping[str, tuple[str, tuple[str, ...]]],
    transaction_repository: TransactionRepository,
) -> None:
    authenticator = _authenticator(credentials)

    @app.get("/v1/portfolio/derived")
    def transaction_derived_portfolio(x_api_key: str | None = Header(default=None)):
        denied = _authorize(authenticator, x_api_key)
        if denied:
            return denied
        try:
            result = _derive(transaction_repository)
        except ValueError as error:
            return JSONResponse(
                {
                    "error": {
                        "code": "PORTFOLIO_ACCOUNTING_BLOCKED",
                        "message": str(error),
                    }
                },
                status_code=409,
            )
        return result.document()


def install_enriched_portfolio_routes(
    app: FastAPI,
    credentials: Mapping[str, tuple[str, tuple[str, ...]]],
    transaction_repository: TransactionRepository,
    presentation_reader: PresentationAssetReader,
) -> None:
    authenticator = _authenticator(credentials)

    @app.get("/v1/portfolio/enriched")
    def certified_enriched_portfolio(x_api_key: str | None = Header(default=None)):
        denied = _authorize(authenticator, x_api_key)
        if denied:
            return denied
        try:
            accounting = _derive(transaction_repository)
            result = enrich_portfolio(accounting, presentation_reader)
        except ValueError as error:
            return JSONResponse(
                {
                    "error": {
                        "code": "PORTFOLIO_ENRICHMENT_BLOCKED",
                        "message": str(error),
                    }
                },
                status_code=409,
            )
        return result.document()
