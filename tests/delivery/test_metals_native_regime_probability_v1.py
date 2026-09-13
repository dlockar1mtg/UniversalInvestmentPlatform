from pathlib import Path
import importlib.util
import json
import math


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_metals_native_regime_probability_sidecar.py"
CONTRACT = ROOT / "config" / "presentation" / "metals_regime_probability_v1.json"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-native-regime-probability-v1-rehearsal.yml"


def _load_module():
    spec = importlib.util.spec_from_file_location("metals_regime_probability_v1", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_contract_is_nonlegacy_commodity_only_and_uncalibrated():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["authority_id"] == "UIP_NATIVE_METALS_REGIME_PROBABILITY_V1"
    assert contract["legacy_equivalent"] is False
    assert contract["scope"] == "BENCHMARK_COMMODITY_ASSET_ONLY"
    assert contract["source_state_mode"] == "CURRENT_CERTIFIED_NATIVE_CYCLE_ONLY"
    assert contract["regime_taxonomy"] == [
        "POSITIVE_TREND",
        "NEUTRAL_OR_MIXED",
        "NEGATIVE_TREND",
    ]
    assert contract["probability_interpretation"] == (
        "DESCRIPTIVE_NORMALIZED_REGIME_SUPPORT_NOT_STATISTICALLY_CALIBRATED"
    )
    assert contract["minimum_evidence"]["insufficient_evidence_behavior"] == "FAIL_CLOSED"
    assert "LEGACY_REGIME_PROBABILITY_COPY_FORWARD" in contract["forbidden_semantics"]
    assert "VEHICLE_RISK_TO_COMMODITY_PROBABILITY_PROJECTION" in contract["forbidden_semantics"]


def test_probability_rule_sums_to_one_and_shrinks_directional_support_by_confidence():
    module = _load_module()
    signal, probs = module.compute_probabilities(
        benchmark_momentum=0.10,
        vehicle_confirmation=0.02,
        confidence=0.60,
        positive_boundary=0.05,
        negative_boundary_abs=0.05,
        benchmark_weight=0.45,
        vehicle_weight=0.35,
        denominator=0.80,
    )
    assert signal > 0
    assert math.isclose(sum(probs.values()), 1.0, rel_tol=0.0, abs_tol=1e-12)
    assert 0.0 <= probs["POSITIVE_TREND"] <= 0.60
    assert probs["NEGATIVE_TREND"] == 0.0
    assert probs["NEUTRAL_OR_MIXED"] >= 0.40


def test_negative_signal_allocates_only_negative_and_neutral_support():
    module = _load_module()
    signal, probs = module.compute_probabilities(
        benchmark_momentum=-0.08,
        vehicle_confirmation=-0.04,
        confidence=0.75,
        positive_boundary=0.05,
        negative_boundary_abs=0.05,
        benchmark_weight=0.45,
        vehicle_weight=0.35,
        denominator=0.80,
    )
    assert signal < 0
    assert probs["POSITIVE_TREND"] == 0.0
    assert probs["NEGATIVE_TREND"] > 0.0
    assert math.isclose(sum(probs.values()), 1.0, rel_tol=0.0, abs_tol=1e-12)


def test_rehearsal_workflow_is_manual_and_does_not_stage_or_activate():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "build_metals_native_regime_probability_sidecar.py" in workflow
    assert "METALS_NATIVE_REGIME_PROBABILITY_V1_REHEARSAL=PASS" in workflow
    assert "production-publication" not in workflow
