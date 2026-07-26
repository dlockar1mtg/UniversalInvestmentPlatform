from __future__ import annotations

import json
from pathlib import Path

from foundation.production.mtg.contracts import (
    validate_marketplace_contract,
    validate_mtg_contracts,
    validate_ownership_registry,
)


def test_repository_contracts_pass() -> None:
    result = validate_mtg_contracts(Path("config/mtg"))
    assert result.status == "PASS"


def test_marketplace_contract_rejects_unsafe_match_threshold(tmp_path: Path) -> None:
    payload = json.loads(Path("config/mtg/marketplace_observation_contract.json").read_text())
    payload["pricing_eligibility"]["minimum_match_score"] = 0.50
    path = tmp_path / "marketplace.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = validate_marketplace_contract(path)
    assert result.status == "FAILED"
    assert "PRICING_MATCH_SCORE_TOO_LOW" in result.reason_codes


def test_ownership_registry_requires_uip_scheduling(tmp_path: Path) -> None:
    payload = json.loads(Path("config/mtg/component_ownership_registry.json").read_text())
    for row in payload["entries"]:
        if row["domain"] == "scheduling":
            row["owner"] = "MTG_SOURCE"
    path = tmp_path / "ownership.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = validate_ownership_registry(path)
    assert result.status == "FAILED"
    assert "OWNERSHIP_MISMATCH:scheduling" in result.reason_codes
