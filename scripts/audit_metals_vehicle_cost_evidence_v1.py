from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_TICKERS = {"GLD","IAU","SGOL","SLV","SIVR","PPLT","CPER","COPX","URA","URNM"}


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

    unresolved_tickers = sorted(row["ticker"] for row in unresolved)
    if unresolved_tickers != ["CPER"]:
        raise RuntimeError(f"Unexpected unresolved cost evidence: {unresolved_tickers}")
    if unresolved[0].get("expense_ratio_pct") is not None:
        raise RuntimeError("CPER unresolved cost must remain missing")

    evidence = {
        "status": "METALS_VEHICLE_COST_EVIDENCE_REHEARSAL_PASS",
        "authority_id": doc["authority_id"],
        "registered_vehicle_count": 10,
        "issuer_cost_observed_count": len(observed),
        "issuer_cost_unresolved_count": len(unresolved),
        "unresolved_tickers": unresolved_tickers,
        "cost_evidence_collection_pass": True,
        "preferred_vehicle_ranking_ready": False,
        "preferred_vehicle_ranking_state": "FAIL_CLOSED_INSUFFICIENT_EVIDENCE",
        "missing_remaining_evidence_families": [
            "CPER_expense_ratio",
            "average_dollar_volume",
            "bid_ask_spread",
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
