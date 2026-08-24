from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "presentation" / "dash_read_1_metals_momentum_read_api_verification.json"


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "DASH-READ-1-METALS-MOMENTUM-READ-API-VERIFY-1":
        raise RuntimeError("unexpected Metals momentum read API verification contract")

    controls = contract.get("controls") or {}
    if controls.get("read_only") is not True:
        raise RuntimeError("read API verification is not governed read-only")
    for key in (
        "tactical_posture_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
        "production_database_write_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited control changed unexpectedly: {key}")

    dsn = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    from foundation.presentation.read_api import PresentationReadRepository

    repository = PresentationReadRepository.from_dsn(dsn)
    metadata = repository.active_metadata()
    if metadata is None:
        raise RuntimeError("no active presentation publication")

    expected_id = str(contract["expected_active_publication_id"])
    expected_fingerprint = str(contract["expected_active_fingerprint"])
    expected_record_count = int(contract["expected_record_count"])
    if str(metadata["publication_id"]) != expected_id:
        raise RuntimeError(f"unexpected active publication: {metadata['publication_id']}")
    if str(metadata["content_fingerprint"]) != expected_fingerprint:
        raise RuntimeError("active presentation fingerprint changed")
    if int(metadata["record_count"]) != expected_record_count:
        raise RuntimeError("active presentation record count changed")

    tickers = ("BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM")
    allowed_states = {
        "ESTABLISHED_UPWARD",
        "STRENGTHENING_UPWARD",
        "WEAKENING_UPWARD",
        "NEUTRAL_CONSOLIDATING",
        "STRENGTHENING_DOWNWARD",
        "ESTABLISHED_DOWNWARD",
        "POTENTIALLY_REVERSING",
    }
    details: list[dict[str, object]] = []
    momentum_count = 0

    for ticker in tickers:
        asset_id = f"metals:vehicle:{ticker}"
        detail = repository.asset_detail("metals", asset_id)
        if detail is None:
            raise RuntimeError(f"read API asset detail missing: {asset_id}")
        grouped = detail.get("records") or {}
        momentum = list(grouped.get(str(contract["record_type"]), []))
        if len(momentum) != 1:
            raise RuntimeError(f"expected exactly one momentum record for {asset_id}")
        momentum_count += 1
        payload = dict(momentum[0]["payload"])
        if payload.get("ticker") != ticker:
            raise RuntimeError(f"ticker mismatch for {asset_id}")
        if payload.get("market_state") not in allowed_states:
            raise RuntimeError(f"unexpected market state for {asset_id}")
        if payload.get("semantic_scope") != contract["semantic_scope"]:
            raise RuntimeError(f"semantic scope changed for {asset_id}")
        if payload.get("source_authority") != contract["source_authority"]:
            raise RuntimeError(f"source authority changed for {asset_id}")
        if payload.get("market_history_authority") != contract["market_history_authority"]:
            raise RuntimeError(f"market-history authority changed for {asset_id}")
        if payload.get("tactical_posture") is not None:
            raise RuntimeError(f"tactical posture unexpectedly populated for {asset_id}")
        if payload.get("cross_domain_rank") is not None:
            raise RuntimeError(f"cross-domain rank unexpectedly populated for {asset_id}")
        if payload.get("automatic_execution_authorized") is not False:
            raise RuntimeError(f"automatic execution unexpectedly authorized for {asset_id}")
        evidence = payload.get("evidence") or {}
        for field in (
            "return_1m_pct",
            "return_3m_pct",
            "return_6m_pct",
            "distance_ma20_pct",
            "distance_ma50_pct",
            "distance_ma200_pct",
            "momentum_acceleration_pct",
        ):
            if field not in evidence or evidence[field] is None:
                raise RuntimeError(f"momentum evidence missing {field} for {asset_id}")
        details.append({
            "asset_id": asset_id,
            "market_state": payload["market_state"],
            "observation_date": payload.get("observation_date"),
            "record_types": sorted(grouped.keys()),
        })

    if momentum_count != int(contract["expected_momentum_record_count"]):
        raise RuntimeError("momentum read API population does not reconcile")

    gold = repository.asset_detail("metals", "metals:vehicle:GLD")
    if gold is None:
        raise RuntimeError("GLD detail missing")
    gold_types = set((gold.get("records") or {}).keys())
    required_gold_types = {"asset", "recommendation", "risk", "metals_momentum_state", "metals_uncertainty_adjusted"}
    if not required_gold_types.issubset(gold_types):
        raise RuntimeError(f"GLD read surface is incomplete: missing={sorted(required_gold_types - gold_types)}")

    result = {
        "status": "PASS",
        "read_only": True,
        "contract_id": contract["contract_id"],
        "active_publication_id": metadata["publication_id"],
        "active_content_fingerprint": metadata["content_fingerprint"],
        "active_record_count": int(metadata["record_count"]),
        "momentum_record_count": momentum_count,
        "asset_details": details,
        "gld_record_types": sorted(gold_types),
        "momentum_state_read_api_verified": True,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "next_decision": contract["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
