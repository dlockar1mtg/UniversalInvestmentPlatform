from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from foundation.import_engine.package import discover_package
from foundation.import_engine.integrity import validate_package_integrity
from foundation.integrations.mtg.universal_adapter import build_universal_mtg_package


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_package(root: Path) -> Path:
    source = root / "source"
    source.mkdir()
    assets = []
    forecasts = []
    recommendations = []
    risks = []
    for index in range(1141):
        asset_id = f"MTG:TEST:{index:04d}"
        assets.append({
            "asset_id": asset_id,
            "asset_name": f"Test Product {index}",
            "asset_class": "MTG",
            "asset_subclass": "SECRET_LAIR" if index < 973 else "COLLECTOR_BOOSTER_BOX",
            "product_class": "SEALED_PRODUCT",
            "source_product_id": f"SRC-{index:04d}",
            "canonical_set_name": "Test Set",
            "release_date": "2025-01-01",
            "registry_status": "ACTIVE",
            "currency": "USD",
        })
        forecast = {
            "asset_id": asset_id,
            "forecast_eligible": "YES" if index < 1103 else "NO",
            "forecast_status": "READY" if index < 1103 else "SUPPRESSED",
            "forecast_method": "TEST",
            "current_market_value_usd": "100",
            "native_forecast_low_usd": "",
            "native_forecast_base_usd": "",
            "native_forecast_high_usd": "",
            "one_year_downside_usd": "",
            "one_year_base_usd": "",
            "one_year_upside_usd": "",
            "three_year_downside_usd": "",
            "three_year_base_usd": "",
            "three_year_upside_usd": "",
            "five_year_downside_usd": "",
            "five_year_base_usd": "",
            "five_year_upside_usd": "",
            "confidence": "0.75",
            "currency": "USD",
        }
        if index < 973:
            forecast.update({
                "native_forecast_low_usd": "90",
                "native_forecast_base_usd": "110",
                "native_forecast_high_usd": "130",
            })
        elif index < 1020 or 1020 <= index < 1103:
            forecast.update({
                "one_year_downside_usd": "95", "one_year_base_usd": "110", "one_year_upside_usd": "125",
                "three_year_downside_usd": "100", "three_year_base_usd": "130", "three_year_upside_usd": "160",
                "five_year_downside_usd": "110", "five_year_base_usd": "150", "five_year_upside_usd": "200",
            })
        forecasts.append(forecast)
        recommendations.append({
            "asset_id": asset_id,
            "recommendation_eligible": "YES" if index < 694 else "NO",
            "recommendation_status": "READY" if index < 694 else "SUPPRESSED",
            "recommendation_action": "WATCH",
            "recommendation_rationale": "Test rationale",
            "suppression_reason": "",
            "confidence": "0.75",
            "currency": "USD",
        })
        risks.append({
            "asset_id": asset_id,
            "admission_tier": "FULL_MODEL",
            "quality_disposition": "ACCEPTED",
            "suppression_reason": "",
            "confidence": "0.75",
            "forecast_eligible": "YES" if index < 1103 else "NO",
            "recommendation_eligible": "YES" if index < 694 else "NO",
        })

    historical_performance = [
        {
            "investment_product_id": f"SL-{index:014d}",
            "universal_mtg_product_id": f"MTG:TEST:{index:04d}",
            "canonical_product_name": f"Test Product {index}",
            "asset_class": "SECRET_LAIR",
            "currency": "USD",
            "historical_performance_status": (
                "HISTORICAL_PERFORMANCE_READY"
                if index < 782
                else "INSUFFICIENT_SPAN"
            ),
            "historical_performance_eligible": (
                "YES" if index < 782 else "NO"
            ),
            "historical_start_date": "2024-01-01",
            "historical_end_date": "2026-07-23",
            "historical_start_value_usd": "100",
            "historical_end_value_usd": "125",
            "historical_elapsed_days": "934",
            "historical_observation_count": "30",
            "historical_distinct_dates": "30",
            "historical_source_count": "2",
            "historical_sources": "TCGCSV|TCGCSV_ARCHIVE_MONTHLY",
            "historical_total_return_pct": (
                "25" if index < 782 else ""
            ),
            "historical_cagr_pct": (
                "8.5" if index < 782 else ""
            ),
            "historical_annualized_return_pct": (
                "8.5" if index < 782 else ""
            ),
            "historical_min_value_usd": "90",
            "historical_max_value_usd": "140",
            "historical_data_quality": (
                "STRONG" if index < 782 else "SHORT_SPAN"
            ),
            "historical_suppression_reason": (
                ""
                if index < 782
                else "REQUIRES_AT_LEAST_30_ELAPSED_DAYS"
            ),
            "forecast_eligible": "NO",
            "recommendation_eligible": "NO",
            "one_year_base_usd": "",
            "three_year_base_usd": "",
            "five_year_base_usd": "",
        }
        for index in range(973)
    ]

    files = {
        "asset_master.csv": (list(assets[0]), assets),
        "forecasts.csv": (list(forecasts[0]), forecasts),
        "recommendations.csv": (list(recommendations[0]), recommendations),
        "risk_metrics.csv": (list(risks[0]), risks),
        "historical_performance.csv": (
            list(historical_performance[0]),
            historical_performance,
        ),
        "portfolio_positions.csv": (
            [
                "position_id",
                "asset_id",
                "quantity",
                "unit_cost_usd",
                "cost_basis_usd",
                "current_unit_value_usd",
                "market_value_usd",
                "currency",
                "source_system",
            ],
            [],
        ),
        "platform_status.csv": (["platform", "interface_name"], [{"platform": "MTG", "interface_name": "mtg-universal-export-v1"}]),
        "diagnostics.csv": (["universal_mtg_product_id", "diagnostic"], []),
    }
    for name, (fields, rows) in files.items():
        _write_csv(source / name, fields, rows)
    manifest = {"files": {name: {"sha256": _sha(source / name)} for name in files}}
    (source / "export_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    summary = {
        "status": "PASS",
        "package_id": "mtg-test-package",
        "delivery_contract": "uip-mtg-delivery-v1",
        "products": 1141,
        "portfolio_positions": 0,
        "diagnostics": 0,
        "historical_performance": {
            "rows": 973,
            "eligible": 782,
            "suppressed": 191,
        },
    }
    (source / "package_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return source


def test_adapter_builds_canonical_universal_package(tmp_path: Path) -> None:
    source = _source_package(tmp_path)
    output = tmp_path / "universal"
    result = build_universal_mtg_package(source, output)
    assert result.dataset_rows == {
        "asset_master": 1141,
        "forecasts": 1363,
        "recommendations": 1141,
        "risk_metrics": 1141,
        "historical_performance": 973,
        "platform_status": 1,
    }
    assert not (output / "portfolio_positions.csv").exists()


def test_adapter_package_passes_existing_import_integrity(tmp_path: Path) -> None:
    output = tmp_path / "universal"
    build_universal_mtg_package(_source_package(tmp_path), output)
    package = discover_package(output)
    validation = validate_package_integrity(package)
    assert validation.passed, validation.issues


def test_adapter_preserves_identity_across_datasets(tmp_path: Path) -> None:
    output = tmp_path / "universal"
    build_universal_mtg_package(_source_package(tmp_path), output)
    with (output / "asset_master.csv").open(encoding="utf-8", newline="") as handle:
        asset_ids = {row["universal_asset_id"] for row in csv.DictReader(handle)}
    for name in ("recommendations.csv", "risk_metrics.csv"):
        with (output / name).open(encoding="utf-8", newline="") as handle:
            assert {
                row["universal_asset_id"]
                for row in csv.DictReader(handle)
            } == asset_ids

    with (
        output / "historical_performance.csv"
    ).open(encoding="utf-8", newline="") as handle:
        historical_ids = {
            row["universal_asset_id"]
            for row in csv.DictReader(handle)
        }

    assert len(historical_ids) == 973
    assert historical_ids <= asset_ids


def test_adapter_declares_privacy_boundary(tmp_path: Path) -> None:
    output = tmp_path / "universal"
    build_universal_mtg_package(_source_package(tmp_path), output)
    summary = json.loads((output / "package_summary.json").read_text(encoding="utf-8"))
    assert summary["position_level_holdings_imported"] is False
    assert summary["source_historical_performance_rows"] == 973
    assert summary["source_historical_performance_eligible"] == 782
    assert summary["source_historical_performance_suppressed"] == 191
    assert summary["source_portfolio_position_rows"] == 0
    assert summary["quota_calls"] == 0
