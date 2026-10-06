"""ETF (Merchants' Guild) package import, presentation records and holdings marked to the package close."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from foundation.presentation import etf_package as E
from foundation.production.hosted_manual_holdings import mark_to_market

ROOT = Path(__file__).resolve().parents[2]


def write_package(directory: Path, *, funds=None, **manifest_changes) -> Path:
    funds = funds if funds is not None else [
        {"ticker": "VOO", "security_id": "SEC-US-VOO", "close": 716.2, "as_of_date": "2026-10-06",
         "quality_status": "PROVISIONAL", "freshness_state": "CURRENT", "call": "STEADY_ACCUMULATION"},
        {"ticker": "IYY", "security_id": "SEC-US-IYY", "close": 189.6, "as_of_date": "2026-10-06",
         "quality_status": "PROVISIONAL", "freshness_state": "CURRENT", "call": "REDIRECT_NEW_MONEY", "redirect_to": "VOO"},
    ]
    files = {
        "funds.json": json.dumps({"as_of_date": "2026-10-06", "model_version": "etf-v1", "funds": funds,
                                  "limitations": [], "automatic_execution_authorized": False}),
        "latest_prices.csv": "security_id,ticker\n",
        "research.json": json.dumps({"timing_rules": {}, "any_rule_passes": False}),
        "market_data_status.json": json.dumps({"funds": []}),
    }
    directory.mkdir(parents=True, exist_ok=True)
    listed = []
    for name, text in files.items():
        (directory / name).write_text(text, encoding="utf-8")
        listed.append({"path": name, "sha256": hashlib.sha256(text.encode()).hexdigest(),
                       "row_count": len(funds) if name == "funds.json" else 0})
    manifest = {"package_id": "etf-2026-10-06-abc123", "domain": "stocks_etf", "contract_version": "1.0.0",
                "generated_at_utc": "2026-10-06T22:30:00+00:00", "source_snapshot_id": "s",
                "repository_commit": "6ed0688", "files": listed, "validation_status": "PASS",
                "certification_status": "PROVISIONAL", "automatic_execution_authorized": False, **manifest_changes}
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


def test_valid_package_becomes_etf_records_beside_the_certified_domains(tmp_path):
    records = E.build_etf_records(write_package(tmp_path / "pkg"), source_run_id="123")
    funds = [r for r in records if r.record_type == "etf_fund"]
    assert {r.record_key for r in funds} == {"VOO", "IYY"}
    assert all(r.domain_id == "etf" for r in records)
    assert all(r.asset_id.startswith("etf:") for r in funds)
    package = next(r for r in records if r.record_type == "etf_package")
    assert package.payload["certification_status"] == "PROVISIONAL"
    assert package.payload["source_run_id"] == "123"
    assert all(r.payload["automatic_execution_authorized"] is False for r in records)
    assert not {"domain_health", "asset", "recommendation"} & {r.record_type for r in records}


@pytest.mark.parametrize("change", [
    {"automatic_execution_authorized": True}, {"domain": "crypto"}, {"validation_status": "FAIL"},
    {"certification_status": "RESEARCH_ONLY"}, {"contract_version": "2.0.0"},
])
def test_contract_breaks_are_refused(tmp_path, change):
    with pytest.raises(E.ETFPackageError):
        E.verify_etf_package(write_package(tmp_path / "pkg", **change))


def test_tampered_or_incomplete_packages_are_refused(tmp_path):
    pkg = write_package(tmp_path / "pkg")
    (pkg / "funds.json").write_text("{}", encoding="utf-8")
    with pytest.raises(E.ETFPackageError, match="digest"):
        E.verify_etf_package(pkg)
    pkg = write_package(tmp_path / "pkg2")
    manifest = json.loads((pkg / "manifest.json").read_text())
    manifest["files"] = [f for f in manifest["files"] if f["path"] != "research.json"]
    (pkg / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(E.ETFPackageError, match="missing"):
        E.verify_etf_package(pkg)


def test_records_only_when_the_cycle_supplies_a_package(tmp_path, monkeypatch):
    monkeypatch.delenv("UIP_ETF_PACKAGE_DIR", raising=False)
    assert E.etf_records_from_environment() == []
    monkeypatch.setenv("UIP_ETF_PACKAGE_DIR", str(write_package(tmp_path / "pkg")))
    assert len(E.etf_records_from_environment()) == 3


def doc(symbol, asset_type, shares, basis, value):
    return {"symbol": symbol, "asset_type": asset_type, "shares": shares, "cost_basis": basis,
            "current_value": value, "current_price": None, "gain_loss": "0", "return_pct": None, "as_of": "2026-10-01"}


def test_etf_holdings_are_marked_to_the_package_close():
    prices = {"VOO": {"close": "716.20", "as_of_date": "2026-10-06", "quality_status": "PROVISIONAL",
                      "freshness_state": "CURRENT", "package_id": "etf-x"}}
    voo, stock, other = mark_to_market([doc("VOO", "ETF", "0.5", "340", "350"), doc("VOO", "STOCK", "1", "1", "1"),
                                        doc("SCHD", "ETF", "2", "60", "64")], prices)
    assert voo["current_value"] == "358.10" and voo["snapshot_current_value"] == "350"
    assert voo["gain_loss"] == "18.10" and voo["valuation_source"] == "ETF_PACKAGE_CLOSE"
    assert voo["valuation_as_of"] == "2026-10-06"
    assert stock["valuation_source"] == other["valuation_source"] == "MANUAL_SNAPSHOT"
    assert other["current_value"] == "64"


def test_wiring_publication_api_and_cycle():
    model = (ROOT / "foundation/presentation/publication_model.py").read_text()
    assert "records.extend(etf_records_from_environment())" in model
    api = (ROOT / "foundation/presentation/read_api.py").read_text()
    assert '@app.get("/v1/presentation/etf")' in api
    assert "def etf_latest_prices(self)" in api
    run = (ROOT / "scripts/run_production_api.py").read_text()
    assert "market_prices=None if presentation_repository is None else presentation_repository.etf_latest_prices" in run
    cycle = (ROOT / ".github/workflows/production-publication-cycle.yml").read_text()
    assert "source dlockar1mtg/StocksETFIntelligencePlatform etf-market-data.yml" in cycle
    assert 'startswith("etf-production-")' in cycle
    assert "python -m foundation.presentation.etf_package incoming/etf" in cycle
    assert "never blocks the certified domains" in cycle
    assert 'newest="$(last_worked "$token" "$repo" "$workflow")" || newest=""' in cycle


def test_etf_records_leave_the_certified_publication_checks_passing(tmp_path):
    from dataclasses import replace
    from foundation.presentation.publication_service import validate_publication_bundle
    from tests.test_dash_read_1_publication_service import valid_publication

    base = valid_publication()
    with_etf = replace(base, records=base.records + tuple(E.build_etf_records(write_package(tmp_path / "pkg"))))
    validate_publication_bundle(with_etf)
