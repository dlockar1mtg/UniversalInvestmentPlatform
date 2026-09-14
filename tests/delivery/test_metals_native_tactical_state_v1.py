from pathlib import Path
import importlib.util
import json


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_metals_native_tactical_state_sidecar.py"
CONTRACT = ROOT / "config" / "presentation" / "metals_tactical_state_v1.json"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-native-tactical-state-v1-rehearsal.yml"


def _load_module():
    spec = importlib.util.spec_from_file_location("tactical_state_v1", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_tactical_state_classifier_is_deterministic_and_descriptive():
    module = _load_module()

    assert module.classify_tactical_state("BUY", 0.08, "POSITIVE_TREND") == (
        "TACTICAL_SUPPORTIVE",
        "POSITIVE_RECOMMENDATION_POSITIVE_12M_ADJUSTED_RETURN_POSITIVE_REGIME",
    )
    assert module.classify_tactical_state("STRONG_BUY", 0.08, "NEUTRAL_OR_MIXED")[0] == "TACTICAL_POSITIVE_BUT_MIXED"
    assert module.classify_tactical_state("BUY", 0.0, "POSITIVE_TREND")[0] == "TACTICAL_CAUTION"
    assert module.classify_tactical_state("HOLD", 0.03, "POSITIVE_TREND")[0] == "TACTICAL_NEUTRAL"
    assert module.classify_tactical_state("REDUCE", -0.03, "NEGATIVE_TREND")[0] == "TACTICAL_DEFENSIVE"
    assert module.classify_tactical_state("AVOID", -0.03, "NEUTRAL_OR_MIXED")[0] == "TACTICAL_CAUTION"
    assert module.classify_tactical_state("REDUCE", 0.01, "NEGATIVE_TREND")[0] == "TACTICAL_CONFLICT"


def test_contract_is_commodity_only_nonlegacy_and_12_month():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["authority_id"] == "UIP_NATIVE_METALS_TACTICAL_STATE_V1"
    assert contract["schema_version"] == "1.0.0"
    assert contract["methodology_version"] == "1.0.0"
    assert contract["legacy_equivalent"] is False
    assert contract["scope"] == "BENCHMARK_COMMODITY_ASSET_ONLY"
    assert contract["source_state_mode"] == "CURRENT_CERTIFIED_NATIVE_CYCLE_ONLY"
    assert contract["tactical_horizon_months"] == 12
    assert contract["state_interpretation"] == "DESCRIPTIVE_12_MONTH_TACTICAL_ALIGNMENT_NOT_TRADE_INSTRUCTION"
    assert contract["output_grain"] == "ONE_ROW_PER_COMMODITY"
    assert contract["risk_semantics"] == "VEHICLE_ONLY_RISK_V1_EXCLUDED_NO_COMMODITY_PROJECTION"
    assert contract["minimum_evidence"]["insufficient_evidence_behavior"] == "FAIL_CLOSED"


def test_contract_has_complete_taxonomy_and_forbidden_semantics():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert set(contract["taxonomy"]) == {
        "TACTICAL_SUPPORTIVE",
        "TACTICAL_POSITIVE_BUT_MIXED",
        "TACTICAL_NEUTRAL",
        "TACTICAL_CAUTION",
        "TACTICAL_DEFENSIVE",
        "TACTICAL_CONFLICT",
    }
    forbidden = set(contract["forbidden_semantics"])
    assert "LEGACY_TACTICAL_STATE_COPY_FORWARD" in forbidden
    assert "LEGACY_ACTION_MAPPING_REUSE" in forbidden
    assert "LEGACY_CLASSIFIER_REUSE" in forbidden
    assert "VEHICLE_RISK_TO_COMMODITY_TACTICAL_PROJECTION" in forbidden
    assert "VEHICLE_TACTICAL_STATE_TO_COMMODITY_PROJECTION" in forbidden
    assert "MISSING_STATE_DEFAULT_TO_HOLD_OR_WAIT" in forbidden
    assert "CROSS_ASSET_RANKING" in forbidden
    assert "PORTFOLIO_ALLOCATION" in forbidden
    assert "TRADE_SIZING" in forbidden
    assert "AUTOMATIC_EXECUTION" in forbidden


def test_rehearsal_workflow_is_manual_and_does_not_publish():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "build_metals_native_tactical_state_sidecar.py" in workflow
    assert "metals-production-cycle.yml" in workflow
    assert "native_regime_probability_v1" in workflow
    assert "native_uncertainty_adjusted_v1" in workflow
    assert "publication_staged" in workflow
    assert "publication_activated" in workflow
    assert "production-publication-cycle" not in workflow
