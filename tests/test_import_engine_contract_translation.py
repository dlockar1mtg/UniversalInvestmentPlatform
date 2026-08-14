from __future__ import annotations

import json

from foundation.import_engine.loader import _translate_contract_row


def test_forecast_contract_fields_translate_without_zero_imputation():
    columns = [
        "run_id",
        "universal_asset_id",
        "platform_id",
        "forecast_origin_date",
        "forecast_horizon_months",
        "forecast_method",
        "point_forecast",
        "lower_bound",
        "upper_bound",
        "expected_return",
        "probability_positive",
        "confidence_score",
        "scenario",
        "source_system",
        "model_version",
        "generated_at_utc",
        "notes",
        "metadata_json",
    ]

    source = {
        "contract_version": "1.0.0",
        "platform_id": "metals",
        "run_id": "run-1",
        "universal_asset_id": "metals:commodity:gold",
        "forecast_origin_date": "2026-08-14",
        "forecast_horizon_months": "12",
        "forecast_date": "2027-08-14",
        "current_value": "2400",
        "forecast_value_base": "2520",
        "forecast_value_bear": "",
        "forecast_value_bull": "",
        "expected_total_return": "0.05",
        "expected_cagr": "0.05",
        "probability_positive_return": "",
        "forecast_confidence": "70",
        "forecast_method": "native-v1",
        "scenario_name": "base",
        "model_version": "1.0.0",
        "generated_at_utc": "2026-08-14T14:30:00Z",
    }

    translated = _translate_contract_row("forecasts", source, columns)

    assert translated["point_forecast"] == "2520"
    assert translated["lower_bound"] is None
    assert translated["upper_bound"] is None
    assert translated["expected_return"] == "0.05"
    assert translated["probability_positive"] is None
    assert translated["confidence_score"] == "70"
    assert translated["scenario"] == "base"

    metadata = json.loads(translated["metadata_json"])

    assert metadata["unmapped_contract_fields"]["contract_version"] == "1.0.0"
    assert metadata["unmapped_contract_fields"]["forecast_date"] == "2027-08-14"
    assert metadata["unmapped_contract_fields"]["current_value"] == "2400"
    assert metadata["unmapped_contract_fields"]["expected_cagr"] == "0.05"


def test_asset_master_contract_fields_translate_to_history_names():
    columns = [
        "run_id",
        "universal_asset_id",
        "platform_asset_id",
        "platform_id",
        "asset_name",
        "asset_symbol",
        "asset_class",
        "asset_subclass",
        "currency",
        "investable",
        "active",
        "source_system",
        "source_record_id",
        "first_observed_date",
        "last_observed_date",
        "last_updated_at_utc",
        "notes",
        "metadata_json",
    ]

    source = {
        "platform_id": "metals",
        "run_id": "run-1",
        "universal_asset_id": "metals:commodity:gold",
        "platform_asset_id": "GOLD",
        "asset_name": "Gold",
        "asset_symbol": "GOLD",
        "asset_class": "metals",
        "asset_subclass": "commodity_benchmark",
        "currency": "USD",
        "market_or_region": "global",
        "is_active": "true",
        "investable": "true",
        "liquidity_tier": "high",
        "data_source": "UIP-native Metals store",
        "first_available_date": "2026-08-14",
        "last_updated_at_utc": "2026-08-14T14:30:00Z",
    }

    translated = _translate_contract_row("asset_master", source, columns)

    assert translated["active"] == "true"
    assert translated["source_system"] == "UIP-native Metals store"
    assert translated["first_observed_date"] == "2026-08-14"

    metadata = json.loads(translated["metadata_json"])

    assert metadata["unmapped_contract_fields"]["market_or_region"] == "global"
    assert metadata["unmapped_contract_fields"]["liquidity_tier"] == "high"


def test_native_recommendation_aliases_are_preserved():
    columns = [
        "run_id",
        "universal_asset_id",
        "platform_id",
        "recommendation",
        "normalized_score",
        "confidence_score",
        "target_weight",
        "minimum_weight",
        "maximum_weight",
        "rationale",
        "risk_summary",
        "time_horizon_months",
        "source_system",
        "model_version",
        "generated_at_utc",
        "metadata_json",
    ]

    source = {
        "run_id": "run-1",
        "universal_asset_id": "metals:commodity:gold",
        "platform_id": "metals",
        "recommendation_date": "2026-08-14",
        "recommendation": "BUY",
        "recommendation_score": "5.0",
        "confidence": "70",
        "time_horizon_months": "12",
        "rationale": "UIP-native model forecast",
        "model_version": "1.0.0",
        "generated_at_utc": "2026-08-14T14:30:00Z",
    }

    translated = _translate_contract_row(
        "recommendations",
        source,
        columns,
    )

    assert translated["recommendation"] == "BUY"
    assert translated["normalized_score"] == "5.0"
    assert translated["confidence_score"] == "70"
    assert translated["time_horizon_months"] == "12"
    assert translated["rationale"] == "UIP-native model forecast"

    metadata = json.loads(translated["metadata_json"])
    assert (
        metadata["unmapped_contract_fields"]["recommendation_date"]
        == "2026-08-14"
    )


def test_existing_metadata_is_merged_with_unmapped_contract_fields():
    columns = [
        "run_id",
        "universal_asset_id",
        "platform_id",
        "point_forecast",
        "metadata_json",
    ]

    source = {
        "run_id": "run-1",
        "universal_asset_id": "metals:commodity:gold",
        "platform_id": "metals",
        "forecast_value_base": "2520",
        "current_value": "2400",
        "metadata_json": '{"native_authority":"preserved"}',
    }

    translated = _translate_contract_row("forecasts", source, columns)
    metadata = json.loads(translated["metadata_json"])

    assert translated["point_forecast"] == "2520"
    assert metadata["native_authority"] == "preserved"
    assert metadata["unmapped_contract_fields"]["current_value"] == "2400"


def test_mtg_native_authority_has_no_generic_translation_rules():
    columns = [
        "mtg_asset_id",
        "native_rank",
        "native_purchase_status",
    ]

    source = {
        "mtg_asset_id": "secret-lair:example",
        "native_rank": "",
        "native_purchase_status": "",
    }

    translated = _translate_contract_row(
        "mtg_native_authority",
        source,
        columns,
    )

    assert translated["mtg_asset_id"] == "secret-lair:example"
    assert translated["native_rank"] is None
    assert translated["native_purchase_status"] is None
