"""Start hardened UIIP on local or Render-assigned networking."""
from pathlib import Path
import os, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

import uvicorn
from foundation.production.ebay_compliance import EbayComplianceSettings, install_ebay_compliance_routes
from foundation.production.free_staging import FreeStagingSettings, build_neon_repositories
from foundation.production.http_service import HTTPServiceSettings, create_http_app
from foundation.production.live_security import LiveSecuritySettings, install_live_security
from foundation.production.hosted_portfolio import install_hosted_portfolio_routes
from foundation.production.hosted_portfolio_accounting import install_transaction_portfolio_routes, install_enriched_portfolio_routes
from foundation.production.hosted_transactions import install_hosted_transaction_routes
from foundation.production.hosted_external_accounts import install_external_account_performance_routes
from foundation.production.external_account_performance import PostgresExternalAccountPerformanceRepository
from foundation.production.portfolio_persistence import PostgresPortfolioSnapshotRepository
from foundation.production.transaction_persistence import PostgresTransactionRepository
from foundation.presentation.asset_catalog import GovernedAssetCatalogRepository, install_governed_asset_catalog_routes
from foundation.presentation.read_api import PresentationReadRepository, install_presentation_read_routes

repository = None
portfolio_repository = None
transaction_repository = None
external_account_repository = None
presentation_repository = None
asset_catalog_repository = None
if os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    free_settings = FreeStagingSettings.from_environment()
    os.environ.update(free_settings.application_environment())
    repository, _ = build_neon_repositories(free_settings)
    portfolio_repository = PostgresPortfolioSnapshotRepository.from_dsn(free_settings.database_url)
    portfolio_repository.initialize()
    transaction_repository = PostgresTransactionRepository.from_dsn(free_settings.database_url)
    transaction_repository.initialize()
    external_account_repository = PostgresExternalAccountPerformanceRepository.from_dsn(free_settings.database_url)
    external_account_repository.initialize()
    presentation_repository = PresentationReadRepository.from_dsn(free_settings.database_url)
    asset_catalog_repository = GovernedAssetCatalogRepository.from_dsn(free_settings.database_url)
settings = HTTPServiceSettings.from_environment()
app = create_http_app(settings, repository=repository)
if portfolio_repository is not None:
    install_hosted_portfolio_routes(app, settings, portfolio_repository)
if presentation_repository is not None:
    install_presentation_read_routes(app, settings.credentials, presentation_repository)
if asset_catalog_repository is not None:
    install_governed_asset_catalog_routes(app, settings.credentials, asset_catalog_repository)
if external_account_repository is not None:
    install_external_account_performance_routes(app, settings, external_account_repository)
if transaction_repository is not None:
    install_hosted_transaction_routes(
        app,
        settings,
        transaction_repository,
        asset_identity_validator=None if asset_catalog_repository is None else asset_catalog_repository.asset_exists,
    )
    install_transaction_portfolio_routes(
        app,
        settings.credentials,
        transaction_repository,
    )
    if presentation_repository is not None:
        install_enriched_portfolio_routes(
            app,
            settings.credentials,
            transaction_repository,
            presentation_repository,
        )
if os.getenv("EBAY_DELETION_VERIFICATION_TOKEN") and os.getenv("EBAY_DELETION_ENDPOINT_URL"):
    install_ebay_compliance_routes(app, EbayComplianceSettings.from_environment())
install_live_security(app, LiveSecuritySettings.from_environment())
uvicorn.run(app, host=os.getenv("UIIP_HTTP_HOST", "127.0.0.1"), port=int(os.getenv("PORT", os.getenv("UIIP_HTTP_PORT", "8000"))))

