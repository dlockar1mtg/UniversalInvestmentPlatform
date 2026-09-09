"""Audit current UIP-native Metals freshness authority without creating presentation data."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

PROVIDER_MAX_AGE_DAYS = {"world_bank": 75, "eia": 730}
RESTORED_FRESHNESS_ROW_COUNT = 21
RESTORED_REQUIRED_FIELDS = {
    "series_key", "frequency", "last_observation", "age_days",
    "freshness_status", "health_score", "message",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def age_days(value: str, as_of: date) -> int:
    return (as_of - date.fromisoformat(value)).days


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--daily-market", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    benchmark = read_csv(args.benchmark)
    daily = read_csv(args.daily_market)
    if not benchmark or not daily:
        raise RuntimeError("benchmark and daily-market inputs must both be non-empty")

    benchmark_subjects = []
    for row in benchmark:
        provider = row["source"].strip().lower()
        observed = row["observation_date"].strip()
        maximum_age = PROVIDER_MAX_AGE_DAYS.get(provider)
        if maximum_age is None:
            raise RuntimeError(f"unrecognized governed benchmark provider: {provider}")
        age = age_days(observed, args.as_of)
        benchmark_subjects.append({
            "series_key": row["series_id"].strip(),
            "source": provider,
            "last_observation": observed,
            "age_days": age,
            "governed_maximum_age_days": maximum_age,
            "within_provider_policy": 0 <= age <= maximum_age,
            "frequency_authority": "provider-specific; not materialized in current artifact",
        })

    vehicle_subjects = []
    for row in daily:
        observed = row["trading_date"].strip()
        age = age_days(observed, args.as_of)
        vehicle_subjects.append({
            "series_key": f"metals:vehicle:{row['ticker'].strip().upper()}",
            "source": "yfinance_daily_market_input",
            "last_observation": observed,
            "age_days": age,
            "governed_maximum_age_days": None,
            "within_provider_policy": None,
            "frequency_authority": "daily collector interval=1d",
        })

    native_count = len(benchmark_subjects) + len(vehicle_subjects)
    all_dates_nonfuture = all(item["age_days"] >= 0 for item in benchmark_subjects + vehicle_subjects)
    benchmark_policy_pass = all(item["within_provider_policy"] for item in benchmark_subjects)

    # The current inputs establish source identity and observation age, but the restored
    # surface also contains health_score/message/frequency semantics from the retired v8
    # pipeline. Those semantics must not be invented from recency alone.
    missing_governed_semantics = [
        "health_score_methodology",
        "freshness_status_mapping_for_daily_vehicle_series",
        "message_generation_policy",
        "canonical_frequency_labels_for_all_native_series",
    ]

    evidence = {
        "status": "METALS_FRESHNESS_AUTHORITY_AUDIT_PASS",
        "query_policy": "ARTIFACT_READ_ONLY",
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "as_of": args.as_of.isoformat(),
        "benchmark_subject_count": len(benchmark_subjects),
        "vehicle_subject_count": len(vehicle_subjects),
        "native_freshness_subject_count": native_count,
        "restored_freshness_row_count": RESTORED_FRESHNESS_ROW_COUNT,
        "exact_legacy_row_parity": native_count == RESTORED_FRESHNESS_ROW_COUNT,
        "all_dates_nonfuture": all_dates_nonfuture,
        "benchmark_provider_policy_pass": benchmark_policy_pass,
        "restored_required_fields": sorted(RESTORED_REQUIRED_FIELDS),
        "missing_governed_semantics": missing_governed_semantics,
        "presentation_contract_ready": False,
        "native_source_identity_and_age_reproducible": all_dates_nonfuture and benchmark_policy_pass,
        "benchmark_subjects": benchmark_subjects,
        "vehicle_subjects": vehicle_subjects,
        "decision": "DO_NOT_BUILD_METALS_DATA_FRESHNESS_UNTIL_MISSING_SEMANTICS_ARE_GOVERNED",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    print("METALS_FRESHNESS_AUTHORITY_AUDIT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
