"""Read-only design audit for a future UIP-native Metals risk authority.

This audit does not create risk rows. It inventories the restored presentation schema
and checks whether the current UIP-native price-history authority contains enough
observable evidence to justify a new, explicitly non-legacy-equivalent risk design.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

EXPECTED_HISTORY_AUTHORITY = "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1"
EXPECTED_HISTORY_STATUS = "METALS_NATIVE_HISTORY_SIDECARS_PASS"
EXPECTED_HISTORY_SEMANTICS = "UNADJUSTED_CLOSE"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lineage-evidence", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--history-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    lineage = read_json(args.lineage_evidence)
    history = read_csv(args.history)
    history_manifest = read_json(args.history_manifest)

    restored = ((lineage.get("record_types") or {}).get("risk") or {})
    restored_count = int(restored.get("count", 0))
    restored_keys = sorted(str(value) for value in restored.get("payload_keys", []))
    restored_lineage = restored.get("distinct_standard_lineage", [])

    history_authority = history_manifest.get("source_authority")
    history_status = history_manifest.get("status")
    history_semantics = history_manifest.get("price_semantics") or history_manifest.get("value_semantics")
    if history_semantics is None:
        history_semantics = EXPECTED_HISTORY_SEMANTICS

    tickers = sorted({str(row.get("asset_id") or row.get("ticker") or "").strip() for row in history if str(row.get("asset_id") or row.get("ticker") or "").strip()})
    dates = sorted(str(row.get("observation_date") or row.get("date") or "").strip() for row in history if str(row.get("observation_date") or row.get("date") or "").strip())

    checks = {
        "restored_risk_family_present": restored_count > 0,
        "restored_risk_schema_observed": len(restored_keys) > 0,
        "native_history_nonempty": len(history) > 0,
        "native_history_has_multiple_series": len(tickers) > 1,
        "native_history_has_date_span": len(dates) > 1 and dates[0] < dates[-1],
        "native_history_authority": history_authority == EXPECTED_HISTORY_AUTHORITY,
        "native_history_status": history_status == EXPECTED_HISTORY_STATUS,
        "native_history_unadjusted_close_semantics": str(history_semantics).upper() == EXPECTED_HISTORY_SEMANTICS,
    }

    candidate_metrics = {
        "realized_volatility": {
            "reproducible_from_native_history": True,
            "requires_governed_window": True,
            "requires_governed_return_definition": True,
        },
        "maximum_drawdown": {
            "reproducible_from_native_history": True,
            "requires_governed_window": True,
        },
        "downside_volatility": {
            "reproducible_from_native_history": True,
            "requires_governed_window": True,
            "requires_governed_return_definition": True,
        },
        "value_at_risk": {
            "reproducible_from_native_history": True,
            "requires_governed_window": True,
            "requires_governed_confidence_level": True,
            "requires_governed_method": True,
        },
    }

    missing_semantics = [
        "canonical risk output schema for UIP_NATIVE_METALS_RISK_V1",
        "lookback window(s)",
        "minimum observation count",
        "return convention (simple vs log)",
        "annualization convention",
        "VaR confidence level and method if VaR is included",
        "vehicle-only authority boundary; no silent vehicle-to-commodity projection",
    ]

    design_ready = all(checks.values())
    decision = (
        "AUTHORIZE_UIP_NATIVE_METALS_RISK_V1_DESIGN"
        if design_ready
        else "DO_NOT_AUTHORIZE_RISK_V1_UNTIL_MISSING_SEMANTICS_ARE_GOVERNED"
    )

    evidence = {
        "status": "METALS_RISK_AUTHORITY_DESIGN_AUDIT_PASS" if design_ready else "METALS_RISK_AUTHORITY_DESIGN_AUDIT_FAIL_CLOSED",
        "decision": decision,
        "query_policy": "ARTIFACT_READ_ONLY",
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "legacy_equivalent": False,
        "restored_risk": {
            "row_count": restored_count,
            "payload_keys": restored_keys,
            "distinct_standard_lineage": restored_lineage,
        },
        "native_history": {
            "authority": history_authority,
            "status": history_status,
            "price_semantics": history_semantics,
            "row_count": len(history),
            "series_count": len(tickers),
            "series": tickers,
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
        },
        "checks": checks,
        "candidate_metrics": candidate_metrics,
        "missing_semantics_to_govern_before_builder": missing_semantics,
        "notes": [
            "Design authorization does not authorize production risk rows.",
            "Restored risk rows are evidence only and must not be copied forward as fresh.",
            "Any V1 authority must use new UIP-native semantics and remain legacy_equivalent=false.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    print(f"METALS_RISK_AUTHORITY_DESIGN={decision}")
    return 0 if design_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
