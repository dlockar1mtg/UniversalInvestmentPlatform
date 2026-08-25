from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_PACKAGE_ID = "metals-v3-new-unseen-validation-20230822-20260824"
EXPECTED_TICKERS = ["COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM", "BIL"]
FORBIDDEN_KEYS = {
    "forward_return_pct",
    "forward_return_21d_pct",
    "forward_return_63d_pct",
    "forward_return_126d_pct",
    "mae_pct",
    "mfe_pct",
    "candidate_regime",
    "candidate_action_state",
    "validation_result",
}
REQUIRED_KEYS = {
    "asset_id",
    "ticker",
    "observation_date",
    "open_usd",
    "high_usd",
    "low_usd",
    "close_usd",
    "adjusted_close_usd",
    "volume",
    "source_provider",
    "package_id",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    args = parser.parse_args()

    root = Path(args.package_dir)
    require(root.is_dir(), "package directory is missing")
    history_path = root / "metals_v3_new_unseen_validation_history.jsonl"
    coverage_path = root / "coverage.json"
    manifest_path = root / "manifest.json"
    for path in [history_path, coverage_path, manifest_path]:
        require(path.is_file(), f"required package file missing: {path.name}")

    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    require(manifest["package_id"] == EXPECTED_PACKAGE_ID, "unexpected package id")
    require(manifest["authorization_id"] == "METALS-TACTICAL-POLICY-V3-NEW-UNSEEN-VALIDATION-AUTHORIZATION-1", "unexpected authorization id")
    require(manifest["package_role"] == "GENUINELY_NEW_UNSEEN_VALIDATION_HISTORY", "unexpected package role")
    require(manifest["outcome_blind"] is True, "package is not outcome blind")
    require(manifest["package_frozen"] is True, "package is not frozen")
    require(manifest["classifier_executed"] is False, "classifier unexpectedly executed")
    require(manifest["validation_outcomes_calculated"] is False, "validation outcomes were calculated")
    require(manifest["validation_outcomes_inspected"] is False, "validation outcomes were inspected")
    require(manifest["tactical_posture_authorized"] is False, "tactical posture unexpectedly authorized")
    require(manifest["new_validation_outcome_inspection_authorized"] is False, "outcome inspection unexpectedly authorized")
    require(manifest["validation_start_date"] == "2023-08-22", "unexpected validation start")
    require(manifest["validation_end_date"] == "2026-08-24", "unexpected validation end")
    require(manifest["consumed_interval_end_date"] == "2023-08-21", "consumed interval boundary changed")
    require(manifest["source_provider"] == "yfinance", "unexpected provider")
    require(manifest["auto_adjust"] is False, "auto_adjust must remain false")
    require(manifest["required_price_field"] == "close_usd", "unexpected price field")
    require(manifest["required_price_semantics"] == "UNADJUSTED_CLOSE", "unexpected price semantics")
    require(manifest["vehicle_count"] == 11, "unexpected vehicle count")
    require(manifest["opportunity_vehicle_count"] == 10, "unexpected opportunity vehicle count")
    require(manifest["reference_control_vehicle"] == "BIL", "unexpected reference/control vehicle")
    require(manifest["history_file"] == history_path.name, "history filename changed")
    require(manifest["coverage_file"] == coverage_path.name, "coverage filename changed")
    require(manifest["history_sha256"] == sha256_file(history_path), "history hash mismatch")
    require(manifest["coverage_sha256"] == sha256_file(coverage_path), "coverage hash mismatch")
    require(manifest["next_decision"] == "CERTIFY_AND_AUTHORIZE_METALS_TACTICAL_POLICY_V3_NEW_UNSEEN_VALIDATION_OUTCOME_INSPECTION", "unexpected next decision")

    require(coverage["package_id"] == EXPECTED_PACKAGE_ID, "coverage package id mismatch")
    require(coverage["outcome_blind"] is True, "coverage is not outcome blind")
    require(coverage["validation_start_date"] == "2023-08-22", "coverage start changed")
    require(coverage["validation_end_date"] == "2026-08-24", "coverage end changed")
    require(coverage["source_provider"] == "yfinance", "coverage provider changed")
    require(coverage["required_price_semantics"] == "UNADJUSTED_CLOSE", "coverage price semantics changed")
    require(coverage["vehicle_count"] == 11, "coverage vehicle count changed")
    require(coverage["opportunity_vehicle_count"] == 10, "coverage opportunity count changed")
    require(coverage["reference_control_vehicle"] == "BIL", "coverage reference/control changed")
    require(set(coverage["vehicles"]) == set(EXPECTED_TICKERS), "coverage ticker universe changed")

    counts = {ticker: 0 for ticker in EXPECTED_TICKERS}
    first_dates: dict[str, str] = {}
    last_dates: dict[str, str] = {}
    row_count = 0
    with history_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            require(set(row) == REQUIRED_KEYS, f"unexpected history schema at line {line_number}")
            require(not (set(row) & FORBIDDEN_KEYS), f"forbidden outcome/performance field at line {line_number}")
            ticker = row["ticker"]
            require(ticker in counts, f"unexpected ticker at line {line_number}: {ticker}")
            require(row["asset_id"] == f"metals:vehicle:{ticker}", f"asset id mismatch at line {line_number}")
            require(row["source_provider"] == "yfinance", f"provider mismatch at line {line_number}")
            require(row["package_id"] == EXPECTED_PACKAGE_ID, f"package id mismatch at line {line_number}")
            date = row["observation_date"]
            require("2023-08-22" <= date <= "2026-08-24", f"out-of-range row at line {line_number}")
            require(row["close_usd"] is not None and float(row["close_usd"]) > 0, f"invalid raw close at line {line_number}")
            counts[ticker] += 1
            first_dates.setdefault(ticker, date)
            last_dates[ticker] = date
            row_count += 1

    require(row_count == manifest["row_count"], "manifest row count mismatch")
    require(row_count == coverage["row_count"], "coverage row count mismatch")
    for ticker in EXPECTED_TICKERS:
        require(counts[ticker] > 0, f"missing history rows for {ticker}")
        meta = coverage["vehicles"][ticker]
        require(meta["row_count"] == counts[ticker], f"coverage row count mismatch for {ticker}")
        require(meta["first_observation_date"] == first_dates[ticker], f"coverage first date mismatch for {ticker}")
        require(meta["last_observation_date"] == last_dates[ticker], f"coverage last date mismatch for {ticker}")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "package_id": EXPECTED_PACKAGE_ID,
        "package_frozen": True,
        "outcome_blind": True,
        "validation_start_date": manifest["validation_start_date"],
        "validation_end_date": manifest["validation_end_date"],
        "row_count": row_count,
        "vehicle_count": manifest["vehicle_count"],
        "opportunity_vehicle_count": manifest["opportunity_vehicle_count"],
        "reference_control_vehicle": manifest["reference_control_vehicle"],
        "common_observation_count": coverage["common_observation_count"],
        "history_sha256": manifest["history_sha256"],
        "coverage_sha256": manifest["coverage_sha256"],
        "validation_outcomes_inspected": False,
        "new_validation_outcome_inspection_authorized": False,
        "tactical_posture_authorized": False,
        "next_decision": manifest["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
