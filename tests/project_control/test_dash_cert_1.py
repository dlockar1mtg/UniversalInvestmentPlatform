import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CERT_MD = ROOT / "docs" / "project_control" / "DASH_CERT_1_CERTIFICATION.md"
CERT_JSON = ROOT / "docs" / "project_control" / "generated" / "dash_cert_1" / "dash_cert_1_certification.json"
ASSETS = ROOT / "foundation" / "production" / "dashboard_assets"


def test_dash_cert_1_artifact_is_pinned_to_accepted_application_baseline():
    document = json.loads(CERT_JSON.read_text(encoding="utf-8"))
    assert document["certification_id"] == "DASH-CERT-1"
    assert document["status"] == "DASH_CERT_1_ACCEPTED_COMPLETE"
    assert document["accepted_application_commit"] == "e26181e3d328d453aee1581c79e14f68dac3d40f"
    assert document["active_publication"]["publication_id"] == "uip-rich-production-20260921T200442Z-2ed557a8e134"
    assert document["active_publication"]["record_count"] == 14309
    assert document["active_publication"]["content_fingerprint"] == "90de48bf27cce58de2f7e4c7ba7e936d0d5c26a800b95a4a0ea323128abfbd70"
    assert document["active_publication"]["source_database_sha256"] == "2ed557a8e134cd29812579e0fa220e36c17c593b0b27190e4e5339d9a8ce169b"


def test_dash_cert_1_covers_all_primary_surfaces():
    document = json.loads(CERT_JSON.read_text(encoding="utf-8"))
    assert document["accepted_surfaces"] == [
        "Home",
        "Recommendations",
        "Portfolio",
        "Transactions",
        "Refresh & Data Health",
        "Operations",
    ]
    html = (ASSETS / "dashboard.html").read_text(encoding="utf-8")
    for page_id in ("home", "recommendations", "portfolio", "transactions", "refresh-page", "operations"):
        assert f'id="{page_id}"' in html


def test_dash_cert_1_reconciles_portfolio_and_transaction_acceptance_evidence():
    document = json.loads(CERT_JSON.read_text(encoding="utf-8"))
    portfolio = document["portfolio_acceptance"]
    assert portfolio["tracked_components"] == 30
    assert portfolio["certified_port1_positions"] == 25
    assert portfolio["manual_stock_etf_positions"] == 4
    assert portfolio["acorns_accounts"] == 1
    assert portfolio["effective_transactions"] + portfolio["superseded_transactions"] == portfolio["retained_transactions"]
    assert portfolio["retained_transactions"] == 32
    assert portfolio["pricing_coverage"] == "25/25"
    assert portfolio["basis_coverage"] == "25/25"


def test_dash_cert_1_preserves_known_refresh_metadata_deferments():
    document = json.loads(CERT_JSON.read_text(encoding="utf-8"))
    refresh = document["refresh_acceptance"]
    assert refresh["operational_domains_healthy"] == 3
    assert refresh["freshness_review_count"] == 2
    assert refresh["crypto_freshness"] == "CURRENT"
    assert refresh["metals_freshness"] == "STALE"
    assert refresh["mtg_freshness"] == "UNKNOWN"
    assert refresh["last_good_state_preserved"] is True
    assert refresh["source_owned_refresh_preserved"] is True
    assert refresh["manual_hosted_dispatch_exposed"] is False


def test_dash_cert_1_governance_boundaries_remain_explicit():
    document = json.loads(CERT_JSON.read_text(encoding="utf-8"))
    assertions = document["governance_assertions"]
    assert all(assertions.values())
    markdown = CERT_MD.read_text(encoding="utf-8")
    for marker in (
        "no universal cross-domain recommendation rank",
        "no automatic trading or purchasing",
        "missing values",
        "append-only",
        "legacy CSV snapshot",
        "last-good certified authority",
        "source-owned refresh collectors",
    ):
        assert marker in markdown


def test_dash_cert_1_advances_to_remote_production_gate():
    document = json.loads(CERT_JSON.read_text(encoding="utf-8"))
    assert document["next_gate"] == "UIP_REMOTE_PRODUCTION_CERTIFIED"
