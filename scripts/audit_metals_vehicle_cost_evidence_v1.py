from __future__ import annotations

import argparse
import json
from pathlib import Path

_VEHICLE_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "metals" / "vehicles.json"


def _registered_tickers() -> tuple[str, ...]:
    """Enabled, non-reserve Metals implementation vehicles, in registry order."""
    registry = json.loads(_VEHICLE_REGISTRY_PATH.read_text(encoding="utf-8-sig"))
    return tuple(
        str(row["ticker"]).upper()
        for row in registry.get("vehicles", [])
        if row.get("enabled", True) and row.get("role") != "reserve"
    )


EXPECTED_TICKERS = set(_registered_tickers())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default="config/presentation/metals_vehicle_cost_evidence_snapshot_v1.json")
    parser.add_argument("--output", default="data/operations/metals/vehicle_cost_evidence_v1/audit.json")
    args = parser.parse_args()

    doc = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    rows = doc["vehicles"]
    tickers = {row["ticker"] for row in rows}
    if tickers != EXPECTED_TICKERS or len(rows) != 10:
        raise RuntimeError("Vehicle cost evidence snapshot does not cover the exact registered implementation universe")
    if doc.get("ranking_authority") is not False:
        raise RuntimeError("Cost evidence snapshot must not authorize vehicle ranking")

    observed = [row for row in rows if row["status"] == "CERTIFIED_SOURCE_OBSERVED"]
    unresolved = [row for row in rows if row["status"] != "CERTIFIED_SOURCE_OBSERVED"]
    for row in observed:
        value = row.get("expense_ratio_pct")
        if not isinstance(value, (int, float)) or value < 0:
            raise RuntimeError(f"Invalid expense ratio for {row['ticker']}")
        if not str(row.get("source_url", "")).startswith("https://"):
            raise RuntimeError(f"Missing authoritative source URL for {row['ticker']}")
        if not row.get("source_authority") or not row.get("source_as_of"):
            raise RuntimeError(f"Missing provenance for {row['ticker']}")

    if unresolved:
        raise RuntimeError(f"Unexpected unresolved cost evidence: {sorted(row['ticker'] for row in unresolved)}")

    cper = next(row for row in rows if row["ticker"] == "CPER")
    if cper.get("expense_ratio_pct") != 0.88:
        raise RuntimeError("CPER total annual fund operating expenses must equal 0.88%")
    if cper.get("management_fee_pct") != 0.65 or cper.get("other_fund_expenses_pct") != 0.23:
        raise RuntimeError("CPER prospectus component expenses are inconsistent")
    if "sec.gov/Archives/edgar/data/1479247/" not in cper.get("source_url", ""):
        raise RuntimeError("CPER recurring cost must retain the fund-authoritative SEC-filed prospectus source")

    evidence = {
        "status": "METALS_VEHICLE_COST_EVIDENCE_REHEARSAL_PASS",
        "authority_id": doc["authority_id"],
        "registered_vehicle_count": 10,
        "issuer_cost_observed_count": len(observed),
        "issuer_cost_unresolved_count": 0,
        "unresolved_tickers": [],
        "cost_evidence_complete_for_exact_10_tickers": True,
        "cost_evidence_collection_pass": True,
        "preferred_vehicle_ranking_ready": False,
        "preferred_vehicle_ranking_state": "FAIL_CLOSED_REMAINING_EVIDENCE",
        "missing_remaining_evidence_families": [
            "tracking_quality_or_explicit_not_applicable_state"
        ],
        "network_collection_performed": False,
        "publication_write_performed": False,
        "ranking_created": False,
        "automatic_execution_authorized": False
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
