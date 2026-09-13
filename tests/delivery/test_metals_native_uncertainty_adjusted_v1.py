from pathlib import Path
import importlib.util
import json


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_metals_native_uncertainty_adjusted_sidecar.py"
CONTRACT = ROOT / "config" / "presentation" / "metals_uncertainty_adjusted_v1.json"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-native-uncertainty-adjusted-v1-rehearsal.yml"


def _load_module():
    spec = importlib.util.spec_from_file_location("uncertainty_adjusted_v1", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_confidence_haircut_is_conservative_and_monotone():
    module = _load_module()

    penalty, adjusted = module.compute_adjustment(0.20, 0.75)
    assert penalty == 0.05
    assert adjusted == 0.15

    penalty, adjusted = module.compute_adjustment(-0.20, 0.75)
    assert penalty == 0.05
    assert adjusted == -0.25

    penalty, adjusted = module.compute_adjustment(0.20, 1.0)
    assert penalty == 0.0
    assert adjusted == 0.20

    penalty, adjusted = module.compute_adjustment(0.0, 0.25)
    assert penalty == 0.0
    assert adjusted == 0.0

    _, positive_high_confidence = module.compute_adjustment(0.20, 0.90)
    _, positive_low_confidence = module.compute_adjustment(0.20, 0.60)
    assert positive_low_confidence < positive_high_confidence

    _, negative_high_confidence = module.compute_adjustment(-0.20, 0.90)
    _, negative_low_confidence = module.compute_adjustment(-0.20, 0.60)
    assert negative_low_confidence < negative_high_confidence


def test_contract_is_nonlegacy_current_state_and_fail_closed():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["authority_id"] == "UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1"
    assert contract["schema_version"] == "1.0.0"
    assert contract["methodology_version"] == "1.0.0"
    assert contract["legacy_equivalent"] is False
    assert contract["scope"] == "BENCHMARK_COMMODITY_ASSET_BY_FORECAST_HORIZON"
    assert contract["source_state_mode"] == "CURRENT_CERTIFIED_NATIVE_CYCLE_ONLY"
    assert contract["adjusted_quantity"] == "ONE_SIDED_CONFIDENCE_HAIRCUT_EXPECTED_RETURN"
    assert contract["adjustment_interpretation"] == "DESCRIPTIVE_CONSERVATIVE_CONFIDENCE_HAIRCUT_NOT_STATISTICALLY_CALIBRATED_INTERVAL"
    assert contract["output_grain"] == "ONE_ROW_PER_COMMODITY_PER_FORECAST_HORIZON"
    assert contract["regime_semantics"] == "CERTIFIED_REGIME_PROBABILITY_V1_CONTEXT_ONLY_NO_NUMERIC_ADJUSTMENT"
    assert contract["risk_semantics"] == "VEHICLE_ONLY_RISK_V1_EXCLUDED_UNTIL_EXPLICIT_COMMODITY_MAPPING_IS_GOVERNED"
    assert contract["minimum_evidence"]["insufficient_evidence_behavior"] == "FAIL_CLOSED"


def test_contract_forbids_legacy_projection_ranking_allocation_and_execution():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    forbidden = set(contract["forbidden_semantics"])
    assert "STATISTICALLY_CALIBRATED_INTERVAL_CLAIM" in forbidden
    assert "LEGACY_UNCERTAINTY_ADJUSTED_COPY_FORWARD" in forbidden
    assert "VEHICLE_RISK_TO_COMMODITY_ADJUSTMENT_PROJECTION" in forbidden
    assert "REGIME_SUPPORT_NUMERIC_DOUBLE_COUNTING" in forbidden
    assert "COMMODITY_TO_VEHICLE_ADJUSTED_FORECAST_PROJECTION" in forbidden
    assert "CROSS_ASSET_RANKING" in forbidden
    assert "PORTFOLIO_ALLOCATION" in forbidden
    assert "AUTOMATIC_EXECUTION" in forbidden


def test_rehearsal_workflow_is_manual_and_does_not_publish():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "build_metals_native_uncertainty_adjusted_sidecar.py" in workflow
    assert "metals-production-cycle.yml" in workflow
    assert "native_regime_probability_v1" in workflow
    assert "publication_staged" in workflow
    assert "publication_activated" in workflow
    assert "production-publication-cycle" not in workflow
