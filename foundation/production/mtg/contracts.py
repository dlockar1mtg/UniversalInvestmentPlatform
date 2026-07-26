"""Validation helpers for MTG production governance contracts."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ContractValidation:
    status: str
    reason_codes: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_ownership_registry(path: Path) -> ContractValidation:
    if not path.is_file():
        return ContractValidation("FAILED", ("OWNERSHIP_REGISTRY_MISSING",))
    payload = _load(path)
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        return ContractValidation("FAILED", ("OWNERSHIP_ENTRIES_MISSING",))
    reasons: list[str] = []
    by_domain = {str(row.get("domain")): row for row in entries if isinstance(row, dict)}
    required = {
        "product_identity": "MTG_SOURCE",
        "raw_marketplace_observations": "MTG_SOURCE",
        "lane_forecasts": "MTG_SOURCE",
        "certified_export": "MTG_SOURCE",
        "scheduling": "UIP",
        "run_governance": "UIP",
        "universal_import": "UIP",
    }
    for domain, owner in required.items():
        row = by_domain.get(domain)
        if row is None:
            reasons.append(f"OWNERSHIP_DOMAIN_MISSING:{domain}")
        elif row.get("owner") != owner:
            reasons.append(f"OWNERSHIP_MISMATCH:{domain}")
    return ContractValidation("PASS" if not reasons else "FAILED", tuple(reasons or ["OWNERSHIP_REGISTRY_VALID"]))


def validate_marketplace_contract(path: Path) -> ContractValidation:
    if not path.is_file():
        return ContractValidation("FAILED", ("MARKETPLACE_CONTRACT_MISSING",))
    payload = _load(path)
    reasons: list[str] = []
    if payload.get("append_only") is not True:
        reasons.append("MARKETPLACE_CONTRACT_NOT_APPEND_ONLY")
    required_fields = set(payload.get("required_fields") or [])
    required = {
        "observation_id",
        "observed_at_utc",
        "canonical_product_id",
        "marketplace",
        "source_item_id",
        "total_landed_price_usd",
        "match_state",
        "match_score",
        "data_quality_score",
        "collector_run_id",
    }
    missing = sorted(required - required_fields)
    reasons.extend(f"MARKETPLACE_FIELD_MISSING:{field}" for field in missing)
    if set(payload.get("allowed_marketplaces") or []) != {"TCGPLAYER", "EBAY"}:
        reasons.append("MARKETPLACE_SET_INVALID")
    policy = payload.get("pricing_eligibility") or {}
    if policy.get("required_match_state") != "ACCEPTED":
        reasons.append("PRICING_MATCH_STATE_UNSAFE")
    if float(policy.get("minimum_match_score", 0)) < 0.82:
        reasons.append("PRICING_MATCH_SCORE_TOO_LOW")
    return ContractValidation("PASS" if not reasons else "FAILED", tuple(reasons or ["MARKETPLACE_CONTRACT_VALID"]))


def validate_mtg_contracts(config_root: Path) -> ContractValidation:
    ownership = validate_ownership_registry(config_root / "component_ownership_registry.json")
    marketplace = validate_marketplace_contract(config_root / "marketplace_observation_contract.json")
    reasons = tuple(ownership.reason_codes + marketplace.reason_codes)
    status = "PASS" if ownership.passed and marketplace.passed else "FAILED"
    return ContractValidation(status, reasons)
