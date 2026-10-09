"""Macro package import (MacroIntelligencePlatform contract v1: RSI v2.0), records and wiring."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from foundation.presentation import macro_package as MP

ROOT = Path(__file__).resolve().parents[2]


def contract(**changes):
    comps = [{"system": "labor", "component": "payrolls", "score": -1.0, "contribution": -0.12},
             {"system": "financial", "component": "yield_curve", "score": 0.2, "contribution": 0.025}]
    c = {"contract_version": "1.0.0", "domain": "macro", "model_id": "MIHTS_RSI", "model_version": "2.0.0",
         "generated_at_utc": "2026-10-09T14:00:00+00:00", "source_repository": "dlockar1mtg/MacroIntelligencePlatform",
         "source_commit": "abc", "source_run_id": "7", "certification_status": "PROVISIONAL",
         "current": {"as_of_month": "2026-09", "rsi": -0.095, "band": "EXPANSION", "coverage": 1.0, "components": comps, "systems": {}},
         "weights": {}, "anchors": {}, "bands": [], "history": [{"month": "2026-08", "rsi": -0.1}, {"month": "2026-09", "rsi": -0.095}],
         "evaluation": {}, "legacy_snapshots": [{"as_of": "2026-07-17", "rsi_reported": "-0.46", "legacy_unverified": True}],
         "data_freshness": {}, "recession_probability": {"status": "NOT_PUBLISHED"}, "automatic_execution_authorized": False}
    c.update(changes)
    return c


def write(directory: Path, c: dict, **manifest_changes) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    text = json.dumps(c)
    (directory / "macro_uip_contract.json").write_text(text)
    m = {"package_id": "macro-2026-10-09-abc", "domain": "macro", "contract_version": "1.0.0", "generated_at_utc": c["generated_at_utc"],
         "repository_commit": "abc", "files": [{"path": "macro_uip_contract.json", "sha256": hashlib.sha256(text.encode()).hexdigest(),
                                                "row_count": len(c["history"])}],
         "validation_status": "PASS", "certification_status": "PROVISIONAL", "automatic_execution_authorized": False, **manifest_changes}
    (directory / "manifest.json").write_text(json.dumps(m))
    return directory


def test_valid_package_becomes_macro_records(tmp_path):
    recs = MP.build_macro_records(write(tmp_path / "p", contract()), source_run_id="7")
    kinds = {r.record_type: r for r in recs}
    assert set(kinds) == {"macro_reading", "macro_package"}
    assert kinds["macro_reading"].payload["rsi"] == -0.095 and kinds["macro_reading"].domain_id == "macro"
    assert kinds["macro_package"].payload["legacy_snapshots"][0]["legacy_unverified"] is True
    assert all(r.payload["automatic_execution_authorized"] is False for r in recs)


@pytest.mark.parametrize("change,message", [
    (lambda c: c.update(automatic_execution_authorized=True), "authority"),
    (lambda c: c["current"].update(rsi=1.4), "out of range"),
    (lambda c: c["current"].update(band="CALM"), "unknown band"),
    (lambda c: c["current"]["components"][0].update(contribution=-0.5), "add up"),
    (lambda c: c["legacy_snapshots"][0].update(legacy_unverified=False), "unverified"),
    (lambda c: c.update(recession_probability={"status": "PUBLISHED"}), "calibration"),
])
def test_contract_breaks_are_refused(tmp_path, change, message):
    c = contract()
    change(c)
    with pytest.raises(MP.MacroPackageError, match=message):
        MP.verify_macro_package(write(tmp_path / "p", c))


def test_tampering_and_manifest_breaks_are_refused(tmp_path):
    d = write(tmp_path / "p", contract())
    (d / "macro_uip_contract.json").write_text((d / "macro_uip_contract.json").read_text().replace("EXPANSION", "PANIC"))
    with pytest.raises(MP.MacroPackageError, match="digest"):
        MP.verify_macro_package(d)
    with pytest.raises(MP.MacroPackageError, match="status"):
        MP.verify_macro_package(write(tmp_path / "q", contract(), validation_status="FAIL"))


def test_records_only_when_the_cycle_supplies_a_package(tmp_path, monkeypatch):
    monkeypatch.delenv("UIP_MACRO_PACKAGE_DIR", raising=False)
    assert MP.macro_records_from_environment() == []
    monkeypatch.setenv("UIP_MACRO_PACKAGE_DIR", str(write(tmp_path / "p", contract())))
    assert len(MP.macro_records_from_environment()) == 2


def test_wiring_publication_api_cycle_and_watchtower():
    cycle = (ROOT / ".github/workflows/production-publication-cycle.yml").read_text()
    assert "Fetch the provisional macro package (optional, daily; never blocks the certified domains)" in cycle
    assert "source dlockar1mtg/MacroIntelligencePlatform macro-production.yml" in cycle
    assert "UIP_MACRO_PACKAGE_DIR" in cycle and "foundation.presentation.macro_package" in cycle
    assert "macro_records_from_environment" in (ROOT / "foundation/presentation/publication_model.py").read_text()
    assert '@app.get("/v1/presentation/macro")' in (ROOT / "foundation/presentation/read_api.py").read_text()
    assets = ROOT / "foundation/production/dashboard_assets"
    html = (assets / "dashboard.html").read_text()
    assert '<button class="nav-item" data-page="watchtower">' in html and '<section id="watchtower" class="page"' in html
    assert '<script src="/dashboard/assets/watchtower.js" defer></script>' in html
    assert '@app.get("/dashboard/assets/watchtower.js"' in (ROOT / "foundation/production/http_service.py").read_text()
    page = (assets / "watchtower.js").read_text()
    assert page.isascii() and 'call("/v1/presentation/macro")' in page
    for text in ("The storm signs", "The six watch-fires", "How it read before past recessions", "Earlier readings (unverified)",
                 "NOT PUBLISHED", "never trades"):
        assert text in page, text
    for forbidden in ("method:\"POST\"", "localStorage", "eval("):
        assert forbidden not in page
    assert '["macro","The Watchtower \\u00b7 Macro",\'data-rpg-page="watchtower"\']' in (assets / "rpg_realm.js").read_text()
    assert ".rpg-watch-gauge{" in (assets / "rpg_theme.css").read_text()
