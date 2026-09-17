from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config" / "presentation" / "metals_commodity_technical_context_v1.json"
DOC = ROOT / "docs" / "project_control" / "metals_commodity_technical_context_authority_design_v1.md"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_authority_is_direct_commodity_monthly_and_nonlegacy():
    contract = _contract()
    assert contract["authority_id"] == "UIP_NATIVE_METALS_COMMODITY_TECHNICAL_CONTEXT_V1"
    assert contract["schema_version"] == "1.0.0"
    assert contract["methodology_version"] == "1.0.0"
    assert contract["legacy_equivalent"] is False
    assert contract["scope"] == "BENCHMARK_COMMODITY_MONTHLY_TECHNICAL_CONTEXT"
    assert contract["source_contract"]["provider"] == "world_bank"
    assert contract["source_contract"]["required_frequency"] == "MONTHLY"
    assert contract["source_contract"]["required_identity"] == "DIRECT_COMMODITY_BENCHMARK"


def test_supported_universe_is_exact_world_bank_commodity_set_and_uranium_is_unsupported():
    contract = _contract()
    assert set(contract["supported_assets"]) == {
        "metals:commodity:aluminum",
        "metals:commodity:copper",
        "metals:commodity:gold",
        "metals:commodity:nickel",
        "metals:commodity:platinum",
        "metals:commodity:silver",
        "metals:commodity:tin",
        "metals:commodity:zinc",
    }
    assert contract["unsupported_assets"]["metals:commodity:uranium"] == (
        "CERTIFIED_EIA_SOURCE_IS_ANNUAL_AND_CANNOT_SUPPORT_MONTHLY_TECHNICAL_CONTEXT_V1"
    )


def test_monthly_returns_and_drawdown_are_governed_without_imputation():
    contract = _contract()
    metrics = contract["metrics"]
    assert metrics["return_1m"]["formula"] == "latest_value / exact_calendar_month_minus_1_value - 1"
    assert metrics["return_3m"]["formula"] == "latest_value / exact_calendar_month_minus_3_value - 1"
    assert metrics["return_6m"]["formula"] == "latest_value / exact_calendar_month_minus_6_value - 1"
    assert metrics["current_drawdown"]["formula"] == (
        "latest_value / maximum_available_value_through_latest_observation - 1"
    )
    source = contract["source_contract"]
    assert source["vehicle_proxy_allowed"] is False
    assert source["interpolation_allowed"] is False
    assert source["forward_fill_allowed"] is False
    assert source["cross_source_substitution_allowed"] is False


def test_daily_moving_averages_are_explicitly_not_authorized_from_monthly_source():
    contract = _contract()
    policy = contract["moving_average_policy"]
    assert policy["ma50_authorized"] is False
    assert policy["ma200_authorized"] is False
    assert "MONTHLY_WORLD_BANK_HISTORY" in policy["reason"]
    forbidden = set(contract["forbidden_semantics"])
    assert "DAILY_MOVING_AVERAGE_FROM_MONTHLY_SOURCE" in forbidden
    assert "URANIUM_MONTHLY_TECHNICAL_CONTEXT_FROM_ANNUAL_EIA_SOURCE" in forbidden
    assert "VEHICLE_TO_COMMODITY_PROXY_WITHOUT_SEPARATE_AUTHORITY" in forbidden


def test_design_does_not_authorize_publication_execution_or_cron_changes():
    contract = _contract()
    policy = contract["publication_policy"]
    assert policy["source_collection_schedule_change_authorized"] is False
    assert policy["postgres_write_authorized"] is False
    assert policy["presentation_activation_authorized"] is False
    assert policy["central_publication_cron_restoration_authorized"] is False
    text = DOC.read_text(encoding="utf-8")
    assert "No production publication or schedule change is authorized" in text
    assert "URA or URNM price history may not silently stand in" in text
