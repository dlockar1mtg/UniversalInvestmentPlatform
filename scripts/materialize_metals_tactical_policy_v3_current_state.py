from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from execute_metals_tactical_policy_v3_historical_regime_research import (
    build_vehicle_features,
    classify_vehicle,
)

ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_historical_regime_research_freeze.json"
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_post_validation_live_use_authorization.json"

MATERIALIZATION_ID = "METALS-TACTICAL-POLICY-V3-CURRENT-STATE-MATERIALIZATION-1"
SOURCE_PACKAGE_ID = "metals-price-history-20260824"
EXPECTED_HISTORY_SHA = "c3749acbcf3a6d11ee9a6ca392b8421e7654936af489fbb93a2f4ae659470f31"
EXPECTED_CURRENT_SHA = "e18ece1a8dbc5b23f6ec7bb2d014822bdccd8a7f82fca0b6c23d5fda3bc8a4ed"
EXPECTED_SOURCE_MANIFEST_SHA = "82ead8e711e0fde4b30fa4e0e7196681e41e7f0ffa363af201c0ee0737473dcf"
EXPECTED_TICKERS = ["BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"]
ACTION_MAP = {
    "TREND_PERSISTENCE": "TACTICAL_SUPPORTIVE",
    "MEAN_REVERSION_OR_EXHAUSTION": "TACTICAL_DEFENSIVE",
    "NEUTRAL_OR_UNCERTAIN": "NO_TACTICAL_OVERLAY",
}
EXPLANATORY_FIELDS = [
    "return_1m_pct",
    "return_3m_pct",
    "return_6m_pct",
    "distance_ma50_pct",
    "distance_ma200_pct",
    "current_drawdown_pct",
    "realized_volatility_3m_pct",
    "trend_slope",
    "return_dispersion",
    "volatility_change",
    "drawdown_recovery_rate",
    "distance_from_recent_extreme",
    "short_vs_long_momentum_spread",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def find_file_by_sha(root: Path, expected_sha: str, role: str) -> Path:
    matches: list[Path] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if sha256_file(path) == expected_sha:
            matches.append(path)
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {role} file with governed SHA-256; found {len(matches)}")
    return matches[0]


def value_from(row: dict[str, Any], names: tuple[str, ...], role: str) -> Any:
    present = [name for name in names if name in row and row[name] is not None]
    if len(present) != 1:
        raise RuntimeError(f"history row must contain exactly one approved {role} field; found {present}")
    return row[present[0]]


def load_history_jsonl(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            ticker = str(value_from(raw, ("ticker", "vehicle_id", "symbol"), "ticker")).strip().upper()
            observation_date = pd.to_datetime(
                value_from(raw, ("observation_date", "date", "as_of_date"), "date"),
                errors="raise",
            ).date()
            close = float(value_from(raw, ("close_usd", "unadjusted_close", "raw_close", "close"), "unadjusted close"))
            if not ticker or close <= 0:
                raise RuntimeError(f"invalid history row at line {line_number}")
            rows.append({
                "vehicle_id": ticker,
                "observation_date": observation_date,
                "unadjusted_close": close,
            })
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise RuntimeError("certified history is empty")
    if frame.duplicated(["vehicle_id", "observation_date"]).any():
        raise RuntimeError("duplicate vehicle/date rows found in certified history")
    observed = sorted(frame["vehicle_id"].unique().tolist())
    if observed != EXPECTED_TICKERS:
        raise RuntimeError(f"governed live vehicle universe changed: {observed}")
    return frame.sort_values(["vehicle_id", "observation_date"], kind="mergesort").reset_index(drop=True)


def materialize_rows(history: pd.DataFrame, freeze: dict[str, Any]) -> list[dict[str, Any]]:
    latest_dates = history.groupby("vehicle_id")["observation_date"].max().to_dict()
    unique_latest = sorted(set(latest_dates.values()))
    if len(unique_latest) != 1:
        raise RuntimeError(f"latest certified observation is not common across vehicles: {latest_dates}")
    as_of_date = unique_latest[0].isoformat()

    output_rows: list[dict[str, Any]] = []
    for ticker, group in history.groupby("vehicle_id", sort=True):
        group = group.sort_values("observation_date").reset_index(drop=True)
        features = build_vehicle_features(group, freeze)
        labels = classify_vehicle(features, freeze)
        label = labels.iloc[-1]
        if str(label["observation_date"]) != as_of_date:
            raise RuntimeError(f"latest classifier row date mismatch for {ticker}")

        candidate_regime = str(label["candidate_regime"])
        if candidate_regime not in ACTION_MAP:
            raise RuntimeError(f"unmapped candidate regime for {ticker}: {candidate_regime}")
        eligible = bool(label["eligible"])
        is_reference = ticker == "BIL"

        if is_reference:
            tactical_state = "NO_TACTICAL_OVERLAY"
            state_available = False
            state_reason = "REFERENCE_CONTROL_NOT_AN_OPPORTUNITY"
        elif not eligible:
            tactical_state = "NO_TACTICAL_OVERLAY"
            state_available = False
            state_reason = "INSUFFICIENT_POINT_IN_TIME_EVIDENCE"
        else:
            tactical_state = ACTION_MAP[candidate_regime]
            state_available = True
            state_reason = str(label["assignment_reason"])

        row: dict[str, Any] = {
            "asset_id": f"metals:vehicle:{ticker}",
            "ticker": ticker,
            "as_of_date": as_of_date,
            "candidate_regime": candidate_regime,
            "tactical_state": tactical_state,
            "classifier_rule_version": "METALS-V3-REGIME-CANDIDATE-RULES-1",
            "action_mapping_version": "METALS-V3-ACTION-MAPPING-1",
            "price_semantics": "UNADJUSTED_CLOSE",
            "source_package_id": SOURCE_PACKAGE_ID,
            "state_available": state_available,
            "state_reason": state_reason,
            "is_reference_control": is_reference,
        }
        for field in EXPLANATORY_FIELDS:
            value = label[field]
            row[field] = None if pd.isna(value) else float(value)
        output_rows.append(row)

    return sorted(output_rows, key=lambda row: row["ticker"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-package-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    source_root = Path(args.source_package_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not source_root.is_dir():
        raise RuntimeError("certified source package directory is missing")
    if output_dir.exists():
        raise RuntimeError("current-state output directory already exists")

    history_path = find_file_by_sha(source_root, EXPECTED_HISTORY_SHA, "history")
    current_path = find_file_by_sha(source_root, EXPECTED_CURRENT_SHA, "current-price")
    source_manifest_path = find_file_by_sha(source_root, EXPECTED_SOURCE_MANIFEST_SHA, "source manifest")

    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    if freeze.get("freeze_id") != "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-FREEZE-1":
        raise RuntimeError("unexpected frozen classifier authority")
    if auth.get("authorization_id") != "METALS-TACTICAL-POLICY-V3-POST-VALIDATION-LIVE-USE-AUTHORIZATION-1":
        raise RuntimeError("unexpected live-use authorization")
    if auth.get("authorization_decision") != "AUTHORIZE_BOUNDED_METALS_V3_LIVE_TACTICAL_INTERPRETATION":
        raise RuntimeError("bounded live tactical interpretation is not authorized")
    live = auth.get("authorized_live_use", {})
    if live.get("current_state_materialization_authorized") is not True:
        raise RuntimeError("current-state materialization is not authorized")
    if live.get("live_tactical_posture_authorized") is not True:
        raise RuntimeError("live tactical posture is not authorized")
    downstream = auth.get("downstream_authorization_boundary", {})
    if downstream.get("production_database_write_authorized") is not False:
        raise RuntimeError("production database write boundary changed")
    if downstream.get("presentation_activation_authorized") is not False:
        raise RuntimeError("presentation activation boundary changed")
    if downstream.get("network_collection_authorized") is not False:
        raise RuntimeError("network collection boundary changed")

    history = load_history_jsonl(history_path)
    rows = materialize_rows(history, freeze)
    if len(rows) != 11:
        raise RuntimeError("current-state materialization must contain exactly 11 governed vehicles")

    output_dir.mkdir(parents=True, exist_ok=False)
    state_path = output_dir / "metals_v3_current_state.jsonl"
    with state_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    state_sha = sha256_file(state_path)

    manifest = {
        "materialization_id": MATERIALIZATION_ID,
        "authorization_id": auth["authorization_id"],
        "source_package_id": SOURCE_PACKAGE_ID,
        "source_history_file": history_path.name,
        "source_history_sha256": EXPECTED_HISTORY_SHA,
        "source_current_file": current_path.name,
        "source_current_sha256": EXPECTED_CURRENT_SHA,
        "source_manifest_file": source_manifest_path.name,
        "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA,
        "state_file": state_path.name,
        "state_sha256": state_sha,
        "row_count": len(rows),
        "opportunity_row_count": sum(not row["is_reference_control"] for row in rows),
        "reference_control_row_count": sum(row["is_reference_control"] for row in rows),
        "as_of_date": rows[0]["as_of_date"],
        "classifier_rule_version": "METALS-V3-REGIME-CANDIDATE-RULES-1",
        "action_mapping_version": "METALS-V3-ACTION-MAPPING-1",
        "price_semantics": "UNADJUSTED_CLOSE",
        "point_in_time_only": True,
        "network_collection_executed": False,
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "automatic_execution_executed": False,
        "next_decision": "REVIEW_METALS_TACTICAL_POLICY_V3_CURRENT_STATE_MATERIALIZATION",
    }
    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, manifest)

    state_counts: dict[str, int] = {}
    for row in rows:
        state_counts[row["tactical_state"]] = state_counts.get(row["tactical_state"], 0) + 1

    print(json.dumps({
        "status": "PASS",
        "materialization_id": MATERIALIZATION_ID,
        "source_package_id": SOURCE_PACKAGE_ID,
        "as_of_date": manifest["as_of_date"],
        "row_count": manifest["row_count"],
        "opportunity_row_count": manifest["opportunity_row_count"],
        "reference_control_row_count": manifest["reference_control_row_count"],
        "state_sha256": state_sha,
        "state_counts": state_counts,
        "network_collection_executed": False,
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "next_decision": manifest["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
