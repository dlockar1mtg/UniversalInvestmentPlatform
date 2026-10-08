"""Housing package import (HousingIntelligencePlatform contract v1), records and wiring."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from foundation.presentation import housing_package as HP

ROOT = Path(__file__).resolve().parents[2]


def market(name, score, signal, rank):
    return {"market": name, "market_state_as_of": "2025-06-30", "months_behind_latest_input": 14, "entry_score": score,
            "signal": signal, "market_rank": rank, "predicted_12m_growth": 0.0295, "walk_forward_mae": 0.026,
            "calibration": {"status": "FAIL", "correlation": -0.02, "rank_correlation": 0.02, "in_sample": True},
            "best_window": {"months": 36, "prob_neutral_or_better": 0.81}, "outlook": [], "alerts": []}


def write(directory: Path, *, contract_changes=None, manifest_changes=None) -> Path:
    contract = {"contract_version": "1.0.0", "domain": "housing", "model_version": "V10", "generated_at_utc": "2026-10-08T00:00:00+00:00",
                "source_repository": "dlockar1mtg/HousingIntelligencePlatform", "source_commit": "abc", "source_run_id": "9",
                "certification_status": "PROVISIONAL", "data_freshness": {"Zillow ZHVI": "2026-07-31"}, "latest_input_observation": "2026-08-01",
                "markets": [market("Wichita Composite", 49.88, "Neutral / Fair Value", 1), market("DFW Composite", 45.84, "Slight Wait", 2)],
                "known_issues": ["MARKET_STATE_IS_LAST_QUARTER_WITH_A_REALIZED_TARGET"], "warnings": [], "household": None,
                "automatic_execution_authorized": False, **(contract_changes or {})}
    directory.mkdir(parents=True, exist_ok=True)
    text = json.dumps(contract)
    (directory / "housing_uip_contract.json").write_text(text)
    manifest = {"package_id": "housing-2026-10-08-abc", "domain": "housing", "contract_version": "1.0.0",
                "generated_at_utc": contract["generated_at_utc"], "repository_commit": "abc",
                "files": [{"path": "housing_uip_contract.json", "sha256": hashlib.sha256(text.encode()).hexdigest(), "row_count": len(contract["markets"])}],
                "validation_status": "PASS", "certification_status": "PROVISIONAL", "automatic_execution_authorized": False, **(manifest_changes or {})}
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return directory


def test_valid_package_becomes_housing_records(tmp_path):
    records = HP.build_housing_records(write(tmp_path / "pkg"), source_run_id="9")
    markets = [r for r in records if r.record_type == "housing_market"]
    assert {r.record_key for r in markets} == {"wichita-composite", "dfw-composite"}
    assert all(r.domain_id == "housing" and r.payload["automatic_execution_authorized"] is False for r in records)
    package = next(r for r in records if r.record_type == "housing_package")
    assert package.payload["source_run_id"] == "9" and package.payload["market_count"] == 2


@pytest.mark.parametrize("kwargs,message", [
    ({"manifest_changes": {"automatic_execution_authorized": True}}, "automatic"),
    ({"manifest_changes": {"domain": "etf"}}, "domain"),
    ({"manifest_changes": {"validation_status": "FAIL"}}, "status"),
    ({"contract_changes": {"household": {"income": 1}}}, "household"),
    ({"contract_changes": {"markets": [market("Wichita Composite", 140, "Buy", 1), market("DFW Composite", 45, "Slight Wait", 2)]}}, "fails the contract"),
])
def test_contract_breaks_are_refused(tmp_path, kwargs, message):
    with pytest.raises(HP.HousingPackageError, match=message):
        HP.verify_housing_package(write(tmp_path / "pkg", **kwargs))


def test_tampering_is_refused(tmp_path):
    pkg = write(tmp_path / "pkg")
    (pkg / "housing_uip_contract.json").write_text("{}")
    with pytest.raises(HP.HousingPackageError, match="digest"):
        HP.verify_housing_package(pkg)


def test_records_only_when_the_cycle_supplies_a_package(tmp_path, monkeypatch):
    monkeypatch.delenv("UIP_HOUSING_PACKAGE_DIR", raising=False)
    assert HP.housing_records_from_environment() == []
    monkeypatch.setenv("UIP_HOUSING_PACKAGE_DIR", str(write(tmp_path / "pkg")))
    assert len(HP.housing_records_from_environment()) == 3


def test_wiring_publication_api_cycle_and_homestead():
    assert "records.extend(housing_records_from_environment())" in (ROOT / "foundation/presentation/publication_model.py").read_text()
    api = (ROOT / "foundation/presentation/read_api.py").read_text()
    assert '@app.get("/v1/presentation/housing")' in api and "def housing(self)" in api
    cycle = (ROOT / ".github/workflows/production-publication-cycle.yml").read_text()
    assert "dlockar1mtg/HousingIntelligencePlatform" in cycle and 'startswith("housing-production-")' in cycle
    assert "python -m foundation.presentation.housing_package incoming/housing" in cycle
    assert "8*86400" in cycle and "never blocks the certified domains" in cycle
    assert "source dlockar1mtg/HousingIntelligencePlatform housing-production.yml" in cycle
    page = (ROOT / "foundation/production/dashboard_assets/homestead.js").read_text()
    assert 'call("/v1/presentation/housing")' in page and "The housing market" in page and "data-home-use-growth" in page
    assert page.isascii()


def test_housing_records_leave_the_certified_publication_checks_passing(tmp_path):
    from dataclasses import replace
    from foundation.presentation.publication_service import validate_publication_bundle
    from tests.test_dash_read_1_publication_service import valid_publication

    base = valid_publication()
    validate_publication_bundle(replace(base, records=base.records + tuple(HP.build_housing_records(write(tmp_path / "pkg")))))
