from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from materialize_metals_tactical_policy_v3_current_state import (
    ACTION_MAP,
    EXPECTED_CURRENT_SHA,
    EXPECTED_HISTORY_SHA,
    EXPECTED_SOURCE_MANIFEST_SHA,
    EXPECTED_TICKERS,
    MATERIALIZATION_ID,
    SOURCE_PACKAGE_ID,
    find_file_by_sha,
    load_history_jsonl,
    materialize_rows,
)

ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_historical_regime_research_freeze.json"
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_post_validation_live_use_authorization.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-package-dir", required=True)
    parser.add_argument("--materialization-dir", required=True)
    args = parser.parse_args()

    source_root = Path(args.source_package_dir).resolve()
    materialization_root = Path(args.materialization_dir).resolve()
    require(source_root.is_dir(), "certified source package directory is missing")
    require(materialization_root.is_dir(), "current-state materialization directory is missing")

    history_path = find_file_by_sha(source_root, EXPECTED_HISTORY_SHA, "history")
    find_file_by_sha(source_root, EXPECTED_CURRENT_SHA, "current-price")
    find_file_by_sha(source_root, EXPECTED_SOURCE_MANIFEST_SHA, "source manifest")

    state_path = materialization_root / "metals_v3_current_state.jsonl"
    manifest_path = materialization_root / "manifest.json"
    require(state_path.is_file(), "current-state JSONL is missing")
    require(manifest_path.is_file(), "current-state manifest is missing")
    require(sorted(path.name for path in materialization_root.iterdir() if path.is_file()) == ["manifest.json", "metals_v3_current_state.jsonl"], "unexpected materialization files present")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))

    require(manifest["materialization_id"] == MATERIALIZATION_ID, "unexpected materialization id")
    require(manifest["authorization_id"] == "METALS-TACTICAL-POLICY-V3-POST-VALIDATION-LIVE-USE-AUTHORIZATION-1", "authorization id changed")
    require(manifest["source_package_id"] == SOURCE_PACKAGE_ID, "source package id changed")
    require(manifest["source_history_sha256"] == EXPECTED_HISTORY_SHA, "source history hash changed")
    require(manifest["source_current_sha256"] == EXPECTED_CURRENT_SHA, "source current hash changed")
    require(manifest["source_manifest_sha256"] == EXPECTED_SOURCE_MANIFEST_SHA, "source manifest hash changed")
    require(manifest["classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1", "classifier version changed")
    require(manifest["action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1", "mapping version changed")
    require(manifest["price_semantics"] == "UNADJUSTED_CLOSE", "price semantics changed")
    require(manifest["point_in_time_only"] is True, "point-in-time boundary changed")
    require(manifest["network_collection_executed"] is False, "network collection unexpectedly executed")
    require(manifest["production_database_write_executed"] is False, "database write unexpectedly executed")
    require(manifest["presentation_activation_executed"] is False, "presentation activation unexpectedly executed")
    require(manifest["automatic_execution_executed"] is False, "automatic execution unexpectedly executed")
    require(manifest["next_decision"] == "REVIEW_METALS_TACTICAL_POLICY_V3_CURRENT_STATE_MATERIALIZATION", "unexpected next decision")

    require(auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_V3_LIVE_TACTICAL_INTERPRETATION", "live-use authorization changed")
    require(auth["authorized_live_use"]["current_state_materialization_authorized"] is True, "materialization is not authorized")
    require(auth["authorized_live_use"]["live_tactical_posture_authorized"] is True, "live tactical posture is not authorized")
    require(auth["authorized_mapping"] == ACTION_MAP, "authorized mapping changed")

    state_rows = [json.loads(line) for line in state_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    require(len(state_rows) == 11, "current-state row count changed")
    require([row["ticker"] for row in state_rows] == EXPECTED_TICKERS, "current-state ticker universe/order changed")
    require(sum(bool(row["is_reference_control"]) for row in state_rows) == 1, "reference-control count changed")
    require(state_rows[0]["ticker"] == "BIL" and state_rows[0]["state_available"] is False, "BIL reference handling changed")
    require(state_rows[0]["tactical_state"] == "NO_TACTICAL_OVERLAY", "BIL tactical state changed")

    history = load_history_jsonl(history_path)
    expected_rows = materialize_rows(history, freeze)
    require(state_rows == expected_rows, "persisted current-state rows do not exactly match recomputation")

    require(manifest["row_count"] == len(state_rows) == 11, "manifest row count changed")
    require(manifest["opportunity_row_count"] == 10, "opportunity row count changed")
    require(manifest["reference_control_row_count"] == 1, "reference-control row count changed")
    require(manifest["as_of_date"] == state_rows[0]["as_of_date"], "manifest as-of date changed")
    require(len({row["as_of_date"] for row in state_rows}) == 1, "current-state rows do not share one as-of date")
    require(manifest["state_sha256"] == sha256_file(state_path), "current-state SHA-256 mismatch")

    for row in state_rows:
        require(row["classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1", f"classifier version changed for {row['ticker']}")
        require(row["action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1", f"mapping version changed for {row['ticker']}")
        require(row["price_semantics"] == "UNADJUSTED_CLOSE", f"price semantics changed for {row['ticker']}")
        require(row["source_package_id"] == SOURCE_PACKAGE_ID, f"source package changed for {row['ticker']}")
        require(row["candidate_regime"] in ACTION_MAP, f"unexpected regime for {row['ticker']}")
        require(row["tactical_state"] in set(ACTION_MAP.values()), f"unexpected tactical state for {row['ticker']}")
        if row["ticker"] != "BIL" and row["state_available"]:
            require(row["tactical_state"] == ACTION_MAP[row["candidate_regime"]], f"mapping mismatch for {row['ticker']}")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "materialization_id": manifest["materialization_id"],
        "source_package_id": manifest["source_package_id"],
        "as_of_date": manifest["as_of_date"],
        "row_count": manifest["row_count"],
        "opportunity_row_count": manifest["opportunity_row_count"],
        "reference_control_row_count": manifest["reference_control_row_count"],
        "state_sha256": manifest["state_sha256"],
        "live_tactical_posture_authorized": True,
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "next_decision": manifest["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
