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
from foundation.production.portfolio_persistence import PostgresPortfolioSnapshotRepository

repository = None
portfolio_repository = None
if os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    free_settings = FreeStagingSettings.from_environment()
    os.environ.update(free_settings.application_environment())
    repository, _ = build_neon_repositories(free_settings)
    portfolio_repository = PostgresPortfolioSnapshotRepository.from_dsn(free_settings.database_url)
    portfolio_repository.initialize()
settings = HTTPServiceSettings.from_environment()
app = create_http_app(settings, repository=repository)
if portfolio_repository is not None:
    install_hosted_portfolio_routes(app, settings, portfolio_repository)
if os.getenv("EBAY_DELETION_VERIFICATION_TOKEN") and os.getenv("EBAY_DELETION_ENDPOINT_URL"):
    install_ebay_compliance_routes(app, EbayComplianceSettings.from_environment())
install_live_security(app, LiveSecuritySettings.from_environment())
uvicorn.run(app, host=os.getenv("UIIP_HTTP_HOST", "127.0.0.1"), port=int(os.getenv("PORT", os.getenv("UIIP_HTTP_PORT", "8000"))))
