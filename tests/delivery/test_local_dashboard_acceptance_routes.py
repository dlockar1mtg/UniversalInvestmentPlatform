from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_local_dashboard_acceptance_mirrors_hosted_authenticated_routes():
    source = read("scripts/run_local_dashboard_acceptance.py")

    assert "PostgresTransactionRepository" in source
    assert "GovernedAssetCatalogRepository" in source
    assert "install_governed_asset_catalog_routes" in source
    assert "install_hosted_transaction_routes" in source
    assert "install_transaction_portfolio_routes" in source
    assert "install_enriched_portfolio_routes" in source
    assert "asset_identity_validator=asset_catalog_repository.asset_exists" in source


def test_local_dashboard_acceptance_preserves_localhost_only_security():
    source = read("scripts/run_local_dashboard_acceptance.py")

    assert 'allowed_hosts=("127.0.0.1", "localhost")' in source
    assert "require_https=False" in source
    assert 'uvicorn.run(app, host="127.0.0.1", port=port)' in source
    assert "FreeStagingSettings.application_environment()" in source
