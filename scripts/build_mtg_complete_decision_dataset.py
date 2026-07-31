"""Build the complete inclusive MTG decision dataset and tier lists."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_FILES = (
    "asset_master.csv",
    "forecasts.csv",
    "recommendations.csv",
    "risk_metrics.csv",
    "historical_performance.csv",
    "platform_status.csv",
    "export_manifest.json",
)

LANE_ORDER = {
    "COLLECTOR_BOOSTER_BOX": 1,
    "PRE_COLLECTOR_BOOSTER_BOX": 2,
    "SECRET_LAIR": 3,
}

TIER_ORDER = {
    "S": 1,
    "A": 2,
    "B": 3,
    "C": 4,
    "D": 5,
    "WATCH": 6,
    "INSUFFICIENT_DATA": 7,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise RuntimeError(f"CSV has no header: {path}")
        fields = [str(value).strip() for value in reader.fieldnames]
        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append(
                {
                    str(key).strip(): (
                        "" if value is None else str(value).strip()
                    )
                    for key, value in row.items()
                    if key is not None
                }
            )
    return fields, rows


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return payload


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def percentage_points_to_decimal(
    value: Any,
) -> float | None:
    parsed = as_float(value)

    if parsed is None:
        return None

    return parsed / 100.0


def cagr_outlier_status(
    value: float | None,
) -> str:
    if value is None:
        return "NOT_AVAILABLE"

    if value > 3.0:
        return "EXTREME_POSITIVE"

    if value < -0.95:
        return "EXTREME_NEGATIVE"

    if value > 1.0:
        return "HIGH_POSITIVE"

    return "NORMAL"


def capped_cagr_for_scoring(
    value: float | None,
) -> float | None:
    if value is None:
        return None

    return max(
        -1.0,
        min(value, 1.0),
    )


def as_bool(value: Any) -> bool:
    return str(value).strip().upper() in {"YES", "TRUE", "1", "Y"}


def normalize_id(value: Any) -> str:
    return str(value).strip().upper()


def by_id(rows: list[dict[str, str]], field: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        key = normalize_id(row.get(field, ""))
        if not key:
            continue
        if key in result:
            raise RuntimeError(f"Duplicate identifier in {field}: {key}")
        result[key] = row
    return result


def pct_return(current: float | None, future: float | None) -> float | None:
    if current is None or future is None or current <= 0:
        return None
    return (future / current) - 1.0


def quality_points(disposition: str, tier: str) -> float:
    disposition = disposition.upper()
    tier = tier.upper()
    score = {
        "PASS": 18.0,
        "FORECAST_READY": 18.0,
        "EVALUATED": 14.0,
        "PROVISIONAL_GUARDED": 10.0,
        "REVIEW_REQUIRED": 6.0,
        "STRUCTURAL_ONLY": 4.0,
        "STRUCTURAL_SUPPRESSED": 1.0,
        "EXCLUDE_FROM_MODEL": -12.0,
    }.get(disposition, 0.0)

    score += {
        "FULL_MODEL": 8.0,
        "PROVISIONAL_MODEL": 3.0,
        "STRUCTURAL_ONLY": -2.0,
    }.get(tier, 0.0)
    return score


def historical_points(
    eligible: bool,
    status: str,
    data_quality: str,
    cagr: float | None,
) -> float:
    status = status.upper()
    quality = data_quality.upper()

    if not eligible:
        return {
            "INSUFFICIENT_HISTORY": -3.0,
            "INSUFFICIENT_SPAN": -4.0,
            "NO_HISTORY": -8.0,
        }.get(status, -5.0)

    score = {
        "STRONG": 16.0,
        "MODERATE": 11.0,
        "LIMITED": 6.0,
    }.get(quality, 4.0)

    if cagr is not None:
        if cagr >= 0.20:
            score += 12.0
        elif cagr >= 0.10:
            score += 8.0
        elif cagr >= 0.04:
            score += 4.0
        elif cagr >= 0:
            score += 1.0
        elif cagr >= -0.10:
            score -= 4.0
        else:
            score -= 9.0

    return score


def forecast_points(
    eligible: bool,
    method: str,
    current: float | None,
    low: float | None,
    base: float | None,
    high: float | None,
) -> tuple[float, float | None, float | None]:
    base_return = pct_return(current, base)
    downside_return = pct_return(current, low)

    if not eligible:
        score = {
            "NATIVE_MONTE_CARLO_RANGE": 6.0,
            "NATIVE_VALUATION_RANGE": 2.0,
            "NO_NUMERIC_FORECAST": -8.0,
        }.get(method.upper(), 0.0)
        return score, base_return, downside_return

    score = 12.0

    if base_return is not None:
        if base_return >= 0.30:
            score += 17.0
        elif base_return >= 0.15:
            score += 12.0
        elif base_return >= 0.07:
            score += 7.0
        elif base_return >= 0:
            score += 2.0
        else:
            score -= 8.0

    if downside_return is not None:
        if downside_return >= 0:
            score += 5.0
        elif downside_return >= -0.10:
            score += 1.0
        elif downside_return < -0.30:
            score -= 8.0
        elif downside_return < -0.20:
            score -= 5.0

    if high is not None and current is not None and high > current:
        score += 2.0

    return score, base_return, downside_return


def confidence_band(value: float | None) -> str:
    if value is None:
        return "NONE"
    if value >= 75:
        return "HIGH"
    if value >= 55:
        return "MODERATE"
    if value >= 35:
        return "LIMITED"
    return "LOW"


def evidence_confidence(
    confidence: float | None,
    historical_eligible: bool,
    forecast_eligible: bool,
    recommendation_eligible: bool,
) -> str:
    score = 0
    if confidence is not None:
        if confidence >= 75:
            score += 3
        elif confidence >= 55:
            score += 2
        elif confidence >= 35:
            score += 1
    score += 2 if historical_eligible else 0
    score += 2 if forecast_eligible else 0
    score += 1 if recommendation_eligible else 0

    if score >= 7:
        return "HIGH"
    if score >= 4:
        return "MODERATE"
    if score >= 2:
        return "LIMITED"
    return "NONE"


def assign_tier(
    score: float,
    *,
    current_value: float | None,
    historical_eligible: bool,
    historical_cagr: float | None,
    historical_outlier_status: str,
    forecast_eligible: bool,
    recommendation_eligible: bool,
    quality_disposition: str,
) -> str:
    disposition = quality_disposition.upper()

    if current_value is None:
        return "INSUFFICIENT_DATA"

    if disposition in {
        "EXCLUDE_FROM_MODEL",
        "STRUCTURAL_SUPPRESSED",
    }:
        return "D"

    if historical_outlier_status == "EXTREME_NEGATIVE":
        return "D"

    if (
        historical_cagr is not None
        and historical_cagr <= -0.50
    ):
        return "D"

    evidence_count = sum(
        (
            historical_eligible,
            forecast_eligible,
            recommendation_eligible,
        )
    )

    if evidence_count == 0:
        if score >= 58:
            return "C"
        if score >= 40:
            return "D"
        if score >= 25:
            return "WATCH"
        return "INSUFFICIENT_DATA"

    if (
        score >= 82
        and forecast_eligible
        and historical_eligible
    ):
        return "S"

    if (
        score >= 70
        and historical_eligible
        and (
            forecast_eligible
            or recommendation_eligible
        )
    ):
        return "A"

    if score >= 56:
        return "B"

    if score >= 42:
        return "C"
    if score >= 25:
        return "D"
    return "WATCH"


def tier_guardrail_reason(
    historical_cagr: float | None,
    historical_outlier_status: str,
    quality_disposition: str,
) -> str:
    if historical_outlier_status == "EXTREME_NEGATIVE":
        return "EXTREME_NEGATIVE_HISTORICAL_CAGR"

    if (
        historical_cagr is not None
        and historical_cagr <= -0.50
    ):
        return "SEVERE_HISTORICAL_LOSS"

    if quality_disposition.upper() in {
        "EXCLUDE_FROM_MODEL",
        "STRUCTURAL_SUPPRESSED",
    }:
        return "QUALITY_DISPOSITION_CAP"

    return ""


def reason_text(row: dict[str, Any]) -> str:
    reasons: list[str] = []

    if row["historical_performance_eligible"]:
        reasons.append(
            f"historical data {str(row['historical_data_quality']).lower()}"
        )
    else:
        status = row["historical_performance_status"] or "not available"
        reasons.append(f"history {str(status).lower()}")

    if row["forecast_eligible"]:
        reasons.append("forecast eligible")
    else:
        reasons.append("forecast not certified")

    if row["recommendation_eligible"]:
        reasons.append("recommendation eligible")
    else:
        reasons.append("recommendation guarded")

    if row["base_return_pct"] is not None:
        reasons.append(f"base return {row['base_return_pct']:.1%}")

    if row["historical_cagr_pct"] is not None:
        reasons.append(f"historical CAGR {row['historical_cagr_pct']:.1%}")

    return "; ".join(reasons)


def validate_manifest(package: Path, manifest: dict[str, Any]) -> None:
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise RuntimeError("Manifest files object is missing.")

    for filename in REQUIRED_FILES:
        path = package / filename
        if not path.is_file():
            raise RuntimeError(f"Required source file missing: {filename}")

        if filename == "export_manifest.json":
            continue

        entry = files.get(filename)
        if not isinstance(entry, dict):
            raise RuntimeError(f"Manifest entry missing: {filename}")

        expected = str(entry.get("sha256", "")).strip().lower()
        actual = sha256(path)
        if expected != actual:
            raise RuntimeError(
                f"Checksum failed for {filename}: expected={expected}, actual={actual}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    package = args.package.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    manifest = load_json(package / "export_manifest.json")
    validate_manifest(package, manifest)

    _, assets = read_csv(package / "asset_master.csv")
    _, forecasts = read_csv(package / "forecasts.csv")
    _, recommendations = read_csv(package / "recommendations.csv")
    _, risks = read_csv(package / "risk_metrics.csv")
    _, history = read_csv(package / "historical_performance.csv")
    _, platform_rows = read_csv(package / "platform_status.csv")

    forecast_map = by_id(forecasts, "asset_id")
    recommendation_map = by_id(recommendations, "asset_id")
    risk_map = by_id(risks, "asset_id")
    history_map = by_id(history, "universal_mtg_product_id")

    if len(assets) != 1141:
        raise RuntimeError(f"Expected 1,141 assets; found {len(assets)}")

    generated_at = (
        platform_rows[0].get("generated_at_utc", "")
        if platform_rows
        else ""
    )

    records: list[dict[str, Any]] = []

    for asset in assets:
        asset_id = normalize_id(asset.get("asset_id", ""))
        if not asset_id:
            raise RuntimeError("Asset master contains blank asset_id.")

        forecast = forecast_map.get(asset_id)
        recommendation = recommendation_map.get(asset_id)
        risk = risk_map.get(asset_id)
        historical = history_map.get(asset_id)

        if forecast is None or recommendation is None or risk is None:
            raise RuntimeError(f"Missing complete native decision rows: {asset_id}")

        current_value = as_float(forecast.get("current_market_value_usd"))
        low_value = as_float(forecast.get("native_forecast_low_usd"))
        base_value = as_float(forecast.get("native_forecast_base_usd"))
        high_value = as_float(forecast.get("native_forecast_high_usd"))
        confidence = as_float(forecast.get("confidence"))

        forecast_eligible = as_bool(forecast.get("forecast_eligible"))
        recommendation_eligible = as_bool(
            recommendation.get("recommendation_eligible")
        )

        historical_eligible = (
            as_bool(historical.get("historical_performance_eligible"))
            if historical
            else False
        )
        historical_status = (
            historical.get("historical_performance_status", "")
            if historical
            else "NO_HISTORY_RECORD"
        )
        historical_quality = (
            historical.get("historical_data_quality", "")
            if historical
            else "NONE"
        )
        historical_cagr = (
            percentage_points_to_decimal(
                historical.get(
                    "historical_cagr_pct"
                )
            )
            if historical
            else None
        )

        historical_total_return = (
            percentage_points_to_decimal(
                historical.get(
                    "historical_total_return_pct"
                )
            )
            if historical
            else None
        )

        forecast_score, base_return, downside_return = forecast_points(
            forecast_eligible,
            forecast.get("forecast_method", ""),
            current_value,
            low_value,
            base_value,
            high_value,
        )
        historical_outlier_status = (
            cagr_outlier_status(
                historical_cagr
            )
        )

        scoring_cagr = capped_cagr_for_scoring(
            historical_cagr
        )

        history_score = historical_points(
            historical_eligible,
            historical_status,
            historical_quality,
            scoring_cagr,
        )
        quality_score = quality_points(
            risk.get("quality_disposition", ""),
            risk.get("admission_tier", ""),
        )
        confidence_score = 0.0 if confidence is None else confidence * 0.22
        recommendation_score = 8.0 if recommendation_eligible else 0.0

        score = max(
            0.0,
            min(
                100.0,
                20.0
                + forecast_score
                + history_score
                + quality_score
                + confidence_score
                + recommendation_score,
            ),
        )

        record: dict[str, Any] = {
            "package_id": manifest.get("package_id", ""),
            "generated_at_utc": generated_at,
            "asset_id": asset_id,
            "source_product_id": asset.get("source_product_id", ""),
            "tcgplayer_product_id": asset.get("tcgplayer_product_id", ""),
            "asset_name": asset.get("asset_name", ""),
            "asset_class": asset.get("asset_class", ""),
            "asset_subclass": asset.get("asset_subclass", ""),
            "product_class": asset.get("product_class", ""),
            "canonical_set_name": asset.get("canonical_set_name", ""),
            "release_date": asset.get("release_date", ""),
            "currency": asset.get("currency", ""),
            "current_market_value_usd": current_value,
            "native_forecast_low_usd": low_value,
            "native_forecast_base_usd": base_value,
            "native_forecast_high_usd": high_value,
            "base_return_pct": base_return,
            "downside_return_pct": downside_return,
            "forecast_eligible": forecast_eligible,
            "forecast_status": forecast.get("forecast_status", ""),
            "forecast_method": forecast.get("forecast_method", ""),
            "native_confidence": confidence,
            "native_confidence_band": confidence_band(confidence),
            "recommendation_eligible": recommendation_eligible,
            "recommendation_status": recommendation.get(
                "recommendation_status", ""
            ),
            "recommendation_action": recommendation.get(
                "recommendation_action", ""
            ),
            "recommendation_rationale": recommendation.get(
                "recommendation_rationale", ""
            ),
            "suppression_reason": recommendation.get("suppression_reason", ""),
            "admission_tier": risk.get("admission_tier", ""),
            "quality_disposition": risk.get("quality_disposition", ""),
            "quality_flags": risk.get("quality_flags", ""),
            "historical_record_present": historical is not None,
            "historical_performance_eligible": historical_eligible,
            "historical_performance_status": historical_status,
            "historical_data_quality": historical_quality,
            "historical_start_date": (
                historical.get("historical_start_date", "")
                if historical
                else ""
            ),
            "historical_end_date": (
                historical.get("historical_end_date", "")
                if historical
                else ""
            ),
            "historical_observation_count": (
                historical.get("historical_observation_count", "")
                if historical
                else ""
            ),
            "historical_total_return_pct": historical_total_return,
            "historical_cagr_pct": historical_cagr,
            "historical_cagr_scoring_value": (
                scoring_cagr
            ),
            "historical_cagr_outlier_status": (
                historical_outlier_status
            ),
            "historical_suppression_reason": (
                historical.get("historical_suppression_reason", "")
                if historical
                else "NO_HISTORY_RECORD"
            ),
            "decision_score": round(score, 4),
            "tier_guardrail_reason": (
                tier_guardrail_reason(
                    historical_cagr,
                    historical_outlier_status,
                    risk.get(
                        "quality_disposition",
                        "",
                    ),
                )
            ),
            "historical_support": (
                "CERTIFIED"
                if historical_eligible
                else (
                    "LIMITED"
                    if historical is not None
                    else "NONE"
                )
            ),
            "forward_support": (
                "CERTIFIED"
                if forecast_eligible
                else "NOT_CERTIFIED"
            ),
            "purchase_readiness_basis": (
                "HISTORICAL_AND_FORWARD"
                if (
                    historical_eligible
                    and forecast_eligible
                )
                else (
                    "HISTORICAL_ONLY"
                    if historical_eligible
                    else (
                        "FORWARD_ONLY"
                        if forecast_eligible
                        else "PROVISIONAL_ONLY"
                    )
                )
            ),
        }

        record["evidence_confidence"] = evidence_confidence(
            confidence,
            historical_eligible,
            forecast_eligible,
            recommendation_eligible,
        )
        record["investment_tier"] = assign_tier(
            score,
            current_value=current_value,
            historical_eligible=historical_eligible,
            historical_cagr=historical_cagr,
            historical_outlier_status=(
                historical_outlier_status
            ),
            forecast_eligible=forecast_eligible,
            recommendation_eligible=(
                recommendation_eligible
            ),
            quality_disposition=(
                record["quality_disposition"]
            ),
        )
        record["decision_summary"] = reason_text(record)

        records.append(record)

    records.sort(
        key=lambda row: (
            TIER_ORDER.get(
                str(row["investment_tier"]),
                99,
            ),
            -float(row["decision_score"]),
            LANE_ORDER.get(
                str(row["asset_subclass"]),
                99,
            ),
            str(row["asset_name"]).upper(),
        )
    )

    for overall_rank, record in enumerate(
        records,
        start=1,
    ):
        record["overall_rank"] = overall_rank

    lane_rank: Counter[str] = Counter()

    for lane in sorted(
        LANE_ORDER,
        key=LANE_ORDER.get,
    ):
        lane_records = [
            record
            for record in records
            if record["asset_subclass"] == lane
        ]

        lane_records.sort(
            key=lambda row: (
                TIER_ORDER.get(
                    str(row["investment_tier"]),
                    99,
                ),
                -float(row["decision_score"]),
                str(row["asset_name"]).upper(),
            )
        )

        for record in lane_records:
            lane_rank[lane] += 1
            record["lane_rank"] = lane_rank[lane]

    fields = [
        "overall_rank",
        "lane_rank",
        "investment_tier",
        "decision_score",
        "tier_guardrail_reason",
        "evidence_confidence",
        "historical_support",
        "forward_support",
        "purchase_readiness_basis",
        "asset_subclass",
        "asset_name",
        "asset_id",
        "source_product_id",
        "tcgplayer_product_id",
        "canonical_set_name",
        "release_date",
        "current_market_value_usd",
        "native_forecast_low_usd",
        "native_forecast_base_usd",
        "native_forecast_high_usd",
        "base_return_pct",
        "downside_return_pct",
        "forecast_eligible",
        "forecast_status",
        "forecast_method",
        "native_confidence",
        "native_confidence_band",
        "recommendation_eligible",
        "recommendation_status",
        "recommendation_action",
        "recommendation_rationale",
        "admission_tier",
        "quality_disposition",
        "quality_flags",
        "historical_record_present",
        "historical_performance_eligible",
        "historical_performance_status",
        "historical_data_quality",
        "historical_start_date",
        "historical_end_date",
        "historical_observation_count",
        "historical_total_return_pct",
        "historical_cagr_pct",
        "historical_cagr_scoring_value",
        "historical_cagr_outlier_status",
        "suppression_reason",
        "historical_suppression_reason",
        "decision_summary",
        "package_id",
        "generated_at_utc",
        "asset_class",
        "product_class",
        "currency",
    ]

    write_csv(output / "mtg_complete_product_tiers.csv", records, fields)

    filenames = {
        "COLLECTOR_BOOSTER_BOX": "mtg_collector_booster_box_tiers.csv",
        "PRE_COLLECTOR_BOOSTER_BOX": "mtg_pre_collector_booster_box_tiers.csv",
        "SECRET_LAIR": "mtg_secret_lair_tiers.csv",
    }

    for lane, filename in filenames.items():
        lane_rows = [row for row in records if row["asset_subclass"] == lane]
        write_csv(output / filename, lane_rows, fields)

    tier_counts = Counter(
        str(row["investment_tier"])
        for row in records
    )

    lane_counts = Counter(
        str(row["asset_subclass"])
        for row in records
    )

    evidence_counts = Counter(
        str(row["evidence_confidence"])
        for row in records
    )

    lane_tier_counts = {
        lane: dict(
            sorted(
                Counter(
                    str(row["investment_tier"])
                    for row in records
                    if row["asset_subclass"] == lane
                ).items(),
                key=lambda item: TIER_ORDER.get(
                    item[0],
                    99,
                ),
            )
        )
        for lane in sorted(
            LANE_ORDER,
            key=LANE_ORDER.get,
        )
    }

    summary = {
        "status": "PASS",
        "generated_at_utc": utc_now(),
        "source_package": str(package),
        "package_id": manifest.get("package_id"),
        "total_products": len(records),
        "unique_products": len({row["asset_id"] for row in records}),
        "lane_counts": dict(sorted(lane_counts.items())),
        "lane_tier_counts": lane_tier_counts,
        "tier_counts": dict(
            sorted(tier_counts.items(), key=lambda item: TIER_ORDER.get(item[0], 99))
        ),
        "evidence_confidence_counts": dict(sorted(evidence_counts.items())),
        "historical_records_present": sum(
            1 for row in records if row["historical_record_present"]
        ),
        "historical_records_missing": sum(
            1 for row in records if not row["historical_record_present"]
        ),
        "historically_eligible": sum(
            1 for row in records if row["historical_performance_eligible"]
        ),
        "forecast_eligible": sum(
            1 for row in records if row["forecast_eligible"]
        ),
        "recommendation_eligible": sum(
            1 for row in records if row["recommendation_eligible"]
        ),
        "outputs": {
            "complete_master": "mtg_complete_product_tiers.csv",
            "collector_booster_boxes": (
                "mtg_collector_booster_box_tiers.csv"
            ),
            "pre_collector_booster_boxes": (
                "mtg_pre_collector_booster_box_tiers.csv"
            ),
            "secret_lairs": "mtg_secret_lair_tiers.csv",
        },
        "scoring_note": (
            "Inclusive evidence-weighted tiering. Every certified product remains "
            "in the output. Eligibility affects score, tier, and evidence confidence "
            "but never removes a product."
        ),
    }

    if summary["total_products"] != 1141:
        raise RuntimeError("Final decision dataset does not contain 1,141 rows.")
    if summary["unique_products"] != 1141:
        raise RuntimeError("Final decision dataset does not contain 1,141 unique IDs.")
    if summary["lane_counts"] != {
        "COLLECTOR_BOOSTER_BOX": 49,
        "PRE_COLLECTOR_BOOSTER_BOX": 119,
        "SECRET_LAIR": 973,
    }:
        raise RuntimeError(f"Unexpected product-lane reconciliation: {summary['lane_counts']}")
    if summary["historical_records_present"] != 973:
        raise RuntimeError("Historical join did not reconcile to 973 records.")
    if summary["historical_records_missing"] != 168:
        raise RuntimeError("Historical missing count did not reconcile to 168.")

    (output / "mtg_decision_dataset_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("=" * 78)
    print("COMPLETE MTG DECISION DATASET")
    print("=" * 78)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("\nTop 10 overall:")
    for row in records[:10]:
        print(
            f"{row['overall_rank']:>4} | {row['investment_tier']:<17} | "
            f"{row['decision_score']:>7.2f} | "
            f"{row['evidence_confidence']:<8} | "
            f"{row['asset_subclass']:<28} | {row['asset_name']}"
        )
    print("\nOutput:", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
