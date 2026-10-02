import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "rehearse_metals_four_factor_ranking_v1.py"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-four-factor-ranking-v1-rehearsal.yml"
CONFIG = ROOT / "config" / "presentation" / "metals_vehicle_ranking_v1.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("metals_rank", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_ranking_rehearsal_pins_governed_methodology_and_exact_universe():
    text = SCRIPT.read_text(encoding="utf-8")
    # The ranking universe comes from the vehicle registry, not a hard-coded set.
    assert "EXPECTED = set(_registered_tickers())" in text
    assert '"config" / "metals" / "vehicles.json"' in text
    assert 'methodology_version") != "1.2.0"' in text
    assert "ranking_authority" in text
    assert "spread_evidence_certified" in text
    assert "adv_evidence_complete" in text


def test_tie_break_is_deterministic_and_matches_governed_order():
    module = _load_module()
    base = {
        "total_score": 80.0,
        "exposure_fidelity_score": 100.0,
        "bid_ask_spread_bps": 1.0,
        "expense_ratio_pct": 0.2,
        "maximum_drawdown_magnitude": 0.1,
    }
    a = {**base, "ticker": "AAA"}
    b = {**base, "ticker": "BBB"}
    assert sorted([b, a], key=module._tie_key)[0]["ticker"] == "AAA"


def test_governed_normalization_contract_matches_rehearsal_math():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["methodology_version"] == "1.2.0"
    assert config["normalization"]["comparison_scope"] == "WITHIN_SAME_COMMODITY_GROUP_ONLY"
    assert config["normalization"]["single_vehicle_group_policy"] == "DO_NOT_RANK_LABEL_ONLY_REGISTERED_IMPLEMENTATION"
    assert config["normalization"]["missing_required_input_policy"] == "FAIL_CLOSED"
    assert config["normalization"]["zero_or_nonpositive_required_input_policy"] == "FAIL_CLOSED"


def test_workflow_is_manual_only_pins_source_and_preserves_governance_boundaries():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "REHEARSE_METALS_FOUR_FACTOR_RANKING_V1" in text
    assert "metals-production-34849676771" in text
    assert "run-id: 34849676771" in text
    assert "rehearse_metals_four_factor_ranking_v1.py" in text
    assert "preferred_vehicle_labels_authorized" in text
    assert "central_publication_cron_restored" in text
