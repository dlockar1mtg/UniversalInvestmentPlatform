"""Build UIP-native Metals Recommendation Change V1 from read-only native observations."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

import psycopg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_metals_native_cycle_module():
    module_path = ROOT / "foundation" / "production" / "metals_native_cycle.py"
    module_name = "_uip_metals_native_cycle_for_recommendation_change_v1"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load native cycle module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_NATIVE_CYCLE = _load_metals_native_cycle_module()
NativeObservation = _NATIVE_CYCLE.NativeObservation
evaluate_native_cycle = _NATIVE_CYCLE.evaluate_native_cycle
load_methodology = _NATIVE_CYCLE.load_methodology


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_timestamp(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError("missing collected_at_utc")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"invalid collected_at_utc: {text}") from exc
    if parsed.tzinfo is None:
        raise RuntimeError(f"collected_at_utc must be timezone-aware: {text}")
    return parsed


def canonicalize(
    rows: Iterable[dict],
    *,
    id_field: str,
    value_field: str,
    rel_tol: float,
    abs_tol: float,
) -> tuple[list[dict], dict[str, int]]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    raw_count = 0
    for raw in rows:
        raw_count += 1
        item = dict(raw)
        asset_id = str(item.get(id_field) or "").strip()
        date = str(item.get("observation_date") or "").strip()
        if not asset_id or not date:
            raise RuntimeError("native observation missing identity/date")
        value = float(item[value_field])
        if not math.isfinite(value) or value <= 0:
            raise RuntimeError(f"invalid native value for {asset_id} on {date}: {value}")
        item["_parsed_collected_at"] = parse_timestamp(item.get("collected_at_utc"))
        grouped[(asset_id, date)].append(item)

    canonical: list[dict] = []
    duplicate_rows = 0
    superseded_conflicting_rows = 0
    for key, candidates in grouped.items():
        latest_time = max(item["_parsed_collected_at"] for item in candidates)
        latest = [item for item in candidates if item["_parsed_collected_at"] == latest_time]
        chosen_value = float(latest[0][value_field])
        for item in latest[1:]:
            other = float(item[value_field])
            if not math.isclose(chosen_value, other, rel_tol=rel_tol, abs_tol=abs_tol):
                raise RuntimeError(
                    f"conflicting latest-timestamp source values for {key[0]} on {key[1]}: "
                    f"{[float(x[value_field]) for x in latest]}"
                )
        chosen = sorted(
            latest,
            key=lambda item: (str(item.get("source") or ""), str(item.get("run_id") or "")),
        )[0]
        duplicate_rows += max(0, len(candidates) - 1)
        for item in candidates:
            if item is chosen:
                continue
            if item["_parsed_collected_at"] < latest_time and not math.isclose(
                float(item[value_field]),
                float(chosen[value_field]),
                rel_tol=rel_tol,
                abs_tol=abs_tol,
            ):
                superseded_conflicting_rows += 1
        canonical.append({k: v for k, v in chosen.items() if k != "_parsed_collected_at"})

    canonical.sort(key=lambda item: (str(item[id_field]), str(item["observation_date"])))
    return canonical, {
        "raw_row_count": raw_count,
        "canonical_row_count": len(canonical),
        "duplicate_source_rows_collapsed": duplicate_rows,
        "superseded_conflicting_revision_rows": superseded_conflicting_rows,
    }


def recommendations_by_asset(report) -> dict[str, str]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for row in report.forecasts:
        grouped[row.asset_id].add(row.recommendation)
    inconsistent = {asset: sorted(values) for asset, values in grouped.items() if len(values) != 1}
    if inconsistent:
        raise RuntimeError(f"recommendation differs across horizons: {inconsistent}")
    return {asset: next(iter(values)) for asset, values in grouped.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--methodology", type=Path, required=True)
    parser.add_argument("--native-cycle", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    contract = read_json(args.contract)
    methodology = load_methodology(args.methodology)
    native_cycle = read_json(args.native_cycle)

    if contract.get("authority_id") != "UIP_NATIVE_METALS_RECOMMENDATION_CHANGE_V1":
        raise RuntimeError("unexpected recommendation-change authority")
    if contract.get("scope") != "BENCHMARK_COMMODITY_ASSET_ONLY":
        raise RuntimeError("unexpected recommendation-change scope")
    if contract.get("legacy_equivalent") is not False:
        raise RuntimeError("recommendation-change V1 must remain non-legacy-equivalent")
    if native_cycle.get("status") != "PASS":
        raise RuntimeError("current native cycle is not PASS")

    policy = contract.get("same_date_multi_source_policy") or {}
    if policy.get("method") != "LATEST_COLLECTED_REVISION_WINS":
        raise RuntimeError("unsupported same-date revision policy")
    rel_tol = float(policy["latest_timestamp_tie_relative_tolerance"])
    abs_tol = float(policy["latest_timestamp_tie_absolute_tolerance"])

    dsn = os.getenv("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    with psycopg.connect(dsn) as db:
        with db.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(
                "SELECT series_id, observation_date, value, source, collected_at_utc, run_id "
                "FROM metals_observations ORDER BY series_id, observation_date, source"
            )
            benchmark_raw = [
                {
                    "series_id": str(r[0]),
                    "observation_date": str(r[1]),
                    "value": float(r[2]),
                    "source": str(r[3]),
                    "collected_at_utc": str(r[4]),
                    "run_id": str(r[5]),
                }
                for r in cur.fetchall()
            ]
            cur.execute(
                "SELECT ticker, observation_date, COALESCE(adjusted_close, close), source, collected_at_utc, run_id "
                "FROM metals_vehicle_observations ORDER BY ticker, observation_date, source"
            )
            vehicle_raw = [
                {
                    "ticker": str(r[0]),
                    "observation_date": str(r[1]),
                    "value": float(r[2]),
                    "source": str(r[3]),
                    "collected_at_utc": str(r[4]),
                    "run_id": str(r[5]),
                }
                for r in cur.fetchall()
            ]
            db.rollback()

    benchmark, benchmark_stats = canonicalize(
        benchmark_raw, id_field="series_id", value_field="value", rel_tol=rel_tol, abs_tol=abs_tol
    )
    vehicles, vehicle_stats = canonicalize(
        vehicle_raw, id_field="ticker", value_field="value", rel_tol=rel_tol, abs_tol=abs_tol
    )
    if not benchmark or not vehicles:
        raise RuntimeError("canonical native history is empty")

    # The contract requires the union of canonical benchmark and vehicle dates.
    # Do not discard pre-benchmark vehicle observations: they are historical model
    # context and must be present once benchmark forecasts become available.
    evaluation_dates = sorted(
        {str(row["observation_date"]) for row in benchmark}
        | {str(row["observation_date"]) for row in vehicles}
    )

    benchmark_by_date: dict[str, list[dict]] = defaultdict(list)
    vehicle_by_date: dict[str, list[dict]] = defaultdict(list)
    for row in benchmark:
        benchmark_by_date[str(row["observation_date"])].append(row)
    for row in vehicles:
        vehicle_by_date[str(row["observation_date"])].append(row)

    benchmark_seen: list[dict] = []
    vehicle_seen: list[dict] = []
    previous: dict[str, tuple[str, str]] = {}
    changes: list[dict[str, object]] = []
    latest_state: dict[str, str] = {}
    order = {v: i for i, v in enumerate(contract["recommendation_order_worst_to_best"])}

    models = methodology.get("models") or []
    model = models[0] if models and isinstance(models[0], dict) else {}
    source_methodology_version = str(methodology.get("registry_version", ""))
    model_id = str(model.get("model_id", ""))
    if model_id != contract.get("model_id"):
        raise RuntimeError("contract model_id does not match methodology registry")

    for evaluation_date in evaluation_dates:
        benchmark_seen.extend(benchmark_by_date.get(evaluation_date, []))
        vehicle_seen.extend(vehicle_by_date.get(evaluation_date, []))
        benchmark_obs = [
            NativeObservation(str(r["series_id"]), str(r["observation_date"]), float(r["value"]), str(r["source"]))
            for r in benchmark_seen
        ]
        vehicle_obs = [
            NativeObservation(str(r["ticker"]), str(r["observation_date"]), float(r["value"]), str(r["source"]))
            for r in vehicle_seen
        ]
        report = evaluate_native_cycle(benchmark_obs, vehicle_obs, methodology)
        if report.status not in {"PASS", "INCOMPLETE"}:
            raise RuntimeError(f"historical native-cycle replay failed on {evaluation_date}: {report.status}")
        current = recommendations_by_asset(report)
        for asset_id, recommendation in sorted(current.items()):
            if recommendation not in order:
                raise RuntimeError(f"unknown recommendation: {recommendation}")
            if asset_id not in previous:
                previous[asset_id] = (evaluation_date, recommendation)
                continue
            previous_date, previous_recommendation = previous[asset_id]
            if recommendation == previous_recommendation:
                continue
            direction = "UPGRADE" if order[recommendation] > order[previous_recommendation] else "DOWNGRADE"
            changes.append(
                {
                    "universal_asset_id": f"metals:commodity:{asset_id.lower()}",
                    "evaluation_date": evaluation_date,
                    "previous_evaluation_date": previous_date,
                    "previous_recommendation": previous_recommendation,
                    "current_recommendation": recommendation,
                    "transition_direction": direction,
                    "model_id": model_id,
                    "source_methodology_version": source_methodology_version,
                    "authority_id": contract["authority_id"],
                    "methodology_version": contract["methodology_version"],
                    "reconstruction_mode": contract["reconstruction_mode"],
                }
            )
            previous[asset_id] = (evaluation_date, recommendation)
        if current:
            latest_state = current

    expected_current: dict[str, set[str]] = defaultdict(set)
    for row in native_cycle.get("forecasts") or []:
        expected_current[str(row.get("asset_id", "")).strip()].add(str(row.get("recommendation", "")).strip())
    if any(len(values) != 1 for values in expected_current.values()):
        raise RuntimeError("current native cycle is inconsistent across horizons")
    expected_latest = {asset: next(iter(values)) for asset, values in expected_current.items()}
    if contract.get("latest_state_parity_required") and latest_state != expected_latest:
        raise RuntimeError(
            "latest reconstructed recommendation state does not match current native cycle: "
            f"reconstructed={latest_state} current={expected_latest}"
        )

    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "metals_recommendation_change.csv"
    fields = list(contract["required_output_fields"])
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(changes)

    manifest = {
        "status": "METALS_NATIVE_RECOMMENDATION_CHANGE_V1_PASS",
        "authority_id": contract["authority_id"],
        "schema_version": contract["schema_version"],
        "methodology_version": contract["methodology_version"],
        "legacy_equivalent": False,
        "scope": contract["scope"],
        "reconstruction_mode": contract["reconstruction_mode"],
        "model_id": model_id,
        "source_methodology_version": source_methodology_version,
        "evaluation_cadence": contract["evaluation_cadence"],
        "temporal_cutoff_rule": contract["temporal_cutoff_rule"],
        "evaluation_date_count": len(evaluation_dates),
        "first_evaluation_date": evaluation_dates[0] if evaluation_dates else None,
        "last_evaluation_date": evaluation_dates[-1] if evaluation_dates else None,
        "change_row_count": len(changes),
        "changed_asset_count": len({row["universal_asset_id"] for row in changes}),
        "latest_state_asset_count": len(latest_state),
        "latest_state_parity": latest_state == expected_latest,
        "first_observation_behavior": contract["first_observation_behavior"],
        "no_op_behavior": contract["no_op_behavior"],
        "change_event_grain": contract["change_event_grain"],
        "same_date_multi_source_method": policy["method"],
        "benchmark_reconciliation": benchmark_stats,
        "vehicle_reconciliation": vehicle_stats,
        "contract_sha256": sha256_file(args.contract),
        "methodology_registry_sha256": sha256_file(args.methodology),
        "native_cycle_sha256": sha256_file(args.native_cycle),
        "output_sha256": sha256_file(csv_path),
        "postgres_write_performed": False,
        "source_collection_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "vehicle_recommendation_projection_performed": False,
        "legacy_rows_copied_forward": False,
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print("METALS_NATIVE_RECOMMENDATION_CHANGE_V1=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
