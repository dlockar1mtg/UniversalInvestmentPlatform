"""Run the governed dashboard shell locally against the hosted PostgreSQL read model.

This helper is for browser acceptance only. It deliberately preserves production
security policy by constructing a separate localhost-only security configuration
instead of weakening the Render runtime configuration.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn

from foundation.production.free_staging import FreeStagingSettings, build_neon_repositories
from foundation.production.hosted_portfolio import install_hosted_portfolio_routes
from foundation.production.hosted_portfolio_accounting import (
    install_enriched_portfolio_routes,
    install_transaction_portfolio_routes,
)
from foundation.production.hosted_transactions import install_hosted_transaction_routes
from foundation.production.http_service import HTTPServiceSettings, create_http_app
from foundation.production.live_security import LiveSecuritySettings, install_live_security
from foundation.production.portfolio_persistence import PostgresPortfolioSnapshotRepository
from foundation.production.transaction_persistence import PostgresTransactionRepository
from foundation.presentation.asset_catalog import GovernedAssetCatalogRepository, install_governed_asset_catalog_routes
from foundation.presentation.read_api import PresentationReadRepository, install_presentation_read_routes


def require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for local dashboard acceptance")
    return value


def main() -> None:
    database_url = require("UIIP_DATABASE_URL")
    require("UIIP_API_CREDENTIALS_JSON")

    port = int(os.getenv("UIIP_LOCAL_DASHBOARD_PORT", "8011"))
    if not 1 <= port <= 65535:
        raise RuntimeError("UIIP_LOCAL_DASHBOARD_PORT must be a valid TCP port")

    # Reuse the hosted Neon repositories and exact active presentation state, but
    # do not call FreeStagingSettings.application_environment(): that method is
    # intentionally Render-specific and forces HTTPS.
    free_settings = FreeStagingSettings(
        port=port,
        external_hostname="127.0.0.1",
        database_url=database_url,
    )
    production_repository, _ = build_neon_repositories(free_settings)

    portfolio_repository = PostgresPortfolioSnapshotRepository.from_dsn(database_url)
    portfolio_repository.initialize()
    transaction_repository = PostgresTransactionRepository.from_dsn(database_url)
    transaction_repository.initialize()
    presentation_repository = PresentationReadRepository.from_dsn(database_url)
    asset_catalog_repository = GovernedAssetCatalogRepository.from_dsn(database_url)

    local_values = dict(os.environ)
    local_values.update(
        {
            "UIIP_ENVIRONMENT": "development",
            "UIIP_DATABASE_BACKEND": "postgresql",
            "UIIP_DATABASE_URL": database_url,
        }
    )
    settings = HTTPServiceSettings.from_environment(local_values)
    app = create_http_app(settings, repository=production_repository)

    # Mirror the route composition used by the hosted production launcher so the
    # dashboard's authenticated bootstrap cannot fail on locally omitted routes.
    install_hosted_portfolio_routes(app, settings, portfolio_repository)
    install_presentation_read_routes(app, settings.credentials, presentation_repository)
    install_governed_asset_catalog_routes(app, settings.credentials, asset_catalog_repository)
    install_hosted_transaction_routes(
        app,
        settings,
        transaction_repository,
        asset_identity_validator=asset_catalog_repository.asset_exists,
    )
    install_transaction_portfolio_routes(
        app,
        settings.credentials,
        transaction_repository,
    )
    install_enriched_portfolio_routes(
        app,
        settings.credentials,
        transaction_repository,
        presentation_repository,
    )

    # Localhost-only HTTP is permitted solely for this local browser acceptance
    # helper. Production/Render still requires HTTPS through its normal launcher.
    install_live_security(
        app,
        LiveSecuritySettings(
            environment="development",
            allowed_hosts=("127.0.0.1", "localhost"),
            require_https=False,
        ),
    )

    print("=" * 72)
    print("UIP DASH-SHELL-1 LOCAL BROWSER ACCEPTANCE")
    print("=" * 72)
    print(f"Open: http://127.0.0.1:{port}/dashboard")
    print("Local route composition mirrors the hosted dashboard runtime.")
    print("This helper does not weaken the Render HTTPS policy.")
    print("Press Ctrl+C when browser review is complete.")
    print("=" * 72)

    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
