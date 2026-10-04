import json
from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_rich_publication_source_contract.py"
WORKFLOW = ROOT / ".github" / "workflows" / "rich-publication-contract-rehearsal.yml"


def _load_module():
    spec = importlib.util.spec_from_file_location("rich_source_contract", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_mtg_contracts_pin_exact_certified_hashes():
    module = _load_module()
    expected = module.EXPECTED_MTG
    assert expected["premium"]["rows"] == 787
    assert expected["premium"]["sha256"] == "296ccbb9ba96812b99dacd771f1ad311496b4997fa0ac7103e68a1d4aaa03333"
    assert expected["collector"]["sha256"] == "b81ee16a310f8a4f9dcbccf21047e31396df9810d53291cdb9b631fbe046d457"
    assert expected["collector_horizon"]["sha256"] == "585257520197fff9700c0a9f1d1d517af60c1792d944f3f4dab1f65c564cf3e8"
    assert expected["precollector"]["sha256"] == "80d8a60ffcc35d688e6560ee94f2d1f910fb3cd961eea097d5ffd00862034f81"
    assert expected["precollector_scenario"]["sha256"] == "74caad4f8d39ce255455854ab5a5459779f6e73adc0afebc8269e769858aed0a"


def test_metals_native_contracts_cover_exactly_eleven_certified_families():
    module = _load_module()
    contracts = module.NATIVE_METALS_CERTIFIED_CONTRACTS
    assert set(contracts) == {
        "current_price",
        "price_history",
        "data_freshness",
        "commodity_technical_context",
        "platform_health",
        "model_component",
        "risk",
        "recommendation_change",
        "regime_probability",
        "uncertainty_adjusted",
        "tactical_state",
    }
    registry = json.loads((ROOT / "config" / "metals" / "vehicles.json").read_text(encoding="utf-8-sig"))
    registered = sum(1 for row in registry["vehicles"] if row.get("enabled", True))
    assert module.REGISTERED_VEHICLE_COUNT == registered
    assert contracts["current_price"]["expected_rows"] == registered
    assert contracts["data_freshness"]["expected_rows"] == module.FRESHNESS_BENCHMARK_SUBJECTS + registered
    assert contracts["commodity_technical_context"]["expected_rows"] == 8
    assert contracts["platform_health"]["expected_rows"] == 1
    assert contracts["model_component"]["expected_rows"] == 81
    assert contracts["risk"]["expected_rows"] == registered
    assert contracts["recommendation_change"]["minimum_rows"] == 0  # no changes is valid
    assert contracts["regime_probability"]["expected_rows"] == 27
    assert contracts["uncertainty_adjusted"]["expected_rows"] == 27
    assert contracts["tactical_state"]["expected_rows"] == 9
    assert contracts["data_freshness"]["manifest_authority"] == "UIP_NATIVE_METALS_DATA_FRESHNESS_V1"
    assert contracts["commodity_technical_context"]["manifest_authority"] == "UIP_NATIVE_METALS_COMMODITY_TECHNICAL_CONTEXT_V1"
    assert contracts["platform_health"]["manifest_authority"] == "UIP_NATIVE_METALS_PLATFORM_HEALTH_V1"
    assert contracts["model_component"]["manifest_authority"] == "UIP_NATIVE_METALS_MODEL_COMPONENT_V1"
    assert contracts["model_component"]["expected_source_model_ids"] == ["uip-metals-native-trend-v1"]
    assert contracts["risk"]["manifest_authority"] == "UIP_NATIVE_METALS_RISK_V1"
    assert contracts["recommendation_change"]["manifest_authority"] == "UIP_NATIVE_METALS_RECOMMENDATION_CHANGE_V1"
    assert contracts["regime_probability"]["manifest_authority"] == "UIP_NATIVE_METALS_REGIME_PROBABILITY_V1"
    assert contracts["uncertainty_adjusted"]["manifest_authority"] == "UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1"
    assert contracts["tactical_state"]["manifest_authority"] == "UIP_NATIVE_METALS_TACTICAL_STATE_V1"

    expected_technical = contracts["commodity_technical_context"]["expected_manifest_values"]
    assert expected_technical["methodology_version"] == "1.0.0"
    assert expected_technical["scope"] == "BENCHMARK_COMMODITY_MONTHLY_TECHNICAL_CONTEXT"
    assert expected_technical["source_state_mode"] == "CURRENT_CERTIFIED_WORLD_BANK_MONTHLY_HISTORY_ONLY"
    assert expected_technical["presentation_semantics"] == "DESCRIPTIVE_COMMODITY_TECHNICAL_CONTEXT_NOT_RECOMMENDATION_NOT_EXECUTION"
    assert expected_technical["supported_asset_count"] == 8
    assert expected_technical["ma50_supported"] is False
    assert expected_technical["ma200_supported"] is False
    assert expected_technical["source_collection_performed"] is True
    assert set(expected_technical["unsupported_assets"]) == {"metals:commodity:uranium"}

    expected_risk = contracts["risk"]["expected_manifest_values"]
    assert expected_risk["methodology_version"] == "1.0.2"
    assert expected_risk["scope"] == "VEHICLE_ONLY"
    assert expected_risk["same_date_multi_source_method"] == "LATEST_COLLECTED_REVISION_WINS"
    assert expected_risk["source_authority"] == "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1"

    expected_change = contracts["recommendation_change"]["expected_manifest_values"]
    assert expected_change["methodology_version"] == "1.0.0"
    assert expected_change["scope"] == "BENCHMARK_COMMODITY_ASSET_ONLY"
    assert expected_change["reconstruction_mode"] == "RETROSPECTIVE_CANONICAL_OBSERVATION_REPLAY"
    assert expected_change["same_date_multi_source_method"] == "LATEST_COLLECTED_REVISION_WINS"
    assert expected_change["latest_state_parity"] is True
    assert expected_change["vehicle_recommendation_projection_performed"] is False
    assert expected_change["legacy_rows_copied_forward"] is False

    expected_regime = contracts["regime_probability"]["expected_manifest_values"]
    assert expected_regime["methodology_version"] == "1.0.0"
    assert expected_regime["scope"] == "BENCHMARK_COMMODITY_ASSET_ONLY"
    assert expected_regime["source_state_mode"] == "CURRENT_CERTIFIED_NATIVE_CYCLE_ONLY"
    assert expected_regime["probability_interpretation"] == "DESCRIPTIVE_NORMALIZED_REGIME_SUPPORT_NOT_STATISTICALLY_CALIBRATED"
    assert expected_regime["regime_taxonomy"] == ["POSITIVE_TREND", "NEUTRAL_OR_MIXED", "NEGATIVE_TREND"]
    assert expected_regime["statistical_calibration_claimed"] is False
    assert expected_regime["vehicle_risk_projection_performed"] is False
    assert expected_regime["commodity_to_vehicle_regime_projection_performed"] is False
    assert expected_regime["legacy_rows_copied_forward"] is False

    expected_uncertainty = contracts["uncertainty_adjusted"]["expected_manifest_values"]
    assert expected_uncertainty["methodology_version"] == "1.0.0"
    assert expected_uncertainty["scope"] == "BENCHMARK_COMMODITY_ASSET_BY_FORECAST_HORIZON"
    assert expected_uncertainty["source_state_mode"] == "CURRENT_CERTIFIED_NATIVE_CYCLE_ONLY"
    assert expected_uncertainty["adjusted_quantity"] == "ONE_SIDED_CONFIDENCE_HAIRCUT_EXPECTED_RETURN"
    assert expected_uncertainty["adjustment_interpretation"] == "DESCRIPTIVE_CONSERVATIVE_CONFIDENCE_HAIRCUT_NOT_STATISTICALLY_CALIBRATED_INTERVAL"
    assert expected_uncertainty["regime_semantics"] == "CERTIFIED_REGIME_PROBABILITY_V1_CONTEXT_ONLY_NO_NUMERIC_ADJUSTMENT"
    assert expected_uncertainty["risk_semantics"] == "VEHICLE_ONLY_RISK_V1_EXCLUDED_UNTIL_EXPLICIT_COMMODITY_MAPPING_IS_GOVERNED"
    assert expected_uncertainty["statistical_calibration_claimed"] is False
    assert expected_uncertainty["vehicle_risk_projection_performed"] is False
    assert expected_uncertainty["regime_numeric_adjustment_performed"] is False
    assert expected_uncertainty["commodity_to_vehicle_adjusted_projection_performed"] is False
    assert expected_uncertainty["legacy_rows_copied_forward"] is False
    assert expected_uncertainty["cross_asset_ranking_performed"] is False
    assert expected_uncertainty["portfolio_allocation_performed"] is False
    assert expected_uncertainty["automatic_execution_performed"] is False

    expected_tactical = contracts["tactical_state"]["expected_manifest_values"]
    assert expected_tactical["methodology_version"] == "1.0.0"
    assert expected_tactical["scope"] == "BENCHMARK_COMMODITY_ASSET_ONLY"
    assert expected_tactical["source_state_mode"] == "CURRENT_CERTIFIED_NATIVE_CYCLE_ONLY"
    assert expected_tactical["output_grain"] == "ONE_ROW_PER_COMMODITY"
    assert expected_tactical["tactical_horizon_months"] == 12
    assert expected_tactical["state_interpretation"] == "DESCRIPTIVE_12_MONTH_TACTICAL_ALIGNMENT_NOT_TRADE_INSTRUCTION"
    assert expected_tactical["regime_probability_authority_id"] == "UIP_NATIVE_METALS_REGIME_PROBABILITY_V1"
    assert expected_tactical["uncertainty_adjusted_authority_id"] == "UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1"
    assert expected_tactical["risk_semantics"] == "VEHICLE_ONLY_RISK_V1_EXCLUDED_NO_COMMODITY_PROJECTION"
    assert expected_tactical["statistical_calibration_claimed"] is False
    assert expected_tactical["vehicle_risk_projection_performed"] is False
    assert expected_tactical["vehicle_tactical_projection_performed"] is False
    assert expected_tactical["legacy_rows_copied_forward"] is False
    assert expected_tactical["legacy_action_mapping_reused"] is False
    assert expected_tactical["legacy_classifier_reused"] is False
    assert expected_tactical["missing_state_imputed"] is False
    assert expected_tactical["cross_asset_ranking_performed"] is False
    assert expected_tactical["portfolio_allocation_performed"] is False
    assert expected_tactical["trade_sizing_performed"] is False
    assert expected_tactical["automatic_execution_performed"] is False


def test_metals_native_contracts_require_publication_safety_flags():
    module = _load_module()
    assert module.SAFETY_FALSE_KEYS == (
        "postgres_write_performed",
        "publication_staged",
        "publication_activated",
    )
    for family in (
        "data_freshness",
        "commodity_technical_context",
        "platform_health",
        "model_component",
        "risk",
        "recommendation_change",
        "regime_probability",
        "uncertainty_adjusted",
        "tactical_state",
    ):
        assert module.NATIVE_METALS_CERTIFIED_CONTRACTS[family]["require_nonlegacy"] is True


def test_rehearsal_certifies_eleven_of_eleven_without_activating_publication():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert 'assert evidence["status"] == "PASS"' in workflow
    assert 'assert evidence["metals_rich_source_contract_pass"] is True' in workflow
    assert 'assert evidence["metals_certified_family_count"] == 11' in workflow
    assert 'assert evidence["metals_required_family_count"] == 11' in workflow
    assert 'assert evidence["metals_remaining_family_count"] == 0' in workflow
    assert '"risk",' in workflow
    assert '"recommendation_change",' in workflow
    assert '"regime_probability",' in workflow
    assert '"uncertainty_adjusted",' in workflow
    assert '"tactical_state",' in workflow
    assert '"commodity_technical_context",' in workflow
    assert 'test "${{ steps.rich_audit.outputs.audit_status }}" = "0"' in workflow
    assert "RICH_PUBLICATION_RECOVERY_STATE=11_OF_11_SOURCE_CONTRACT_PASS" in workflow
    assert "production-publication-cycle" not in workflow
