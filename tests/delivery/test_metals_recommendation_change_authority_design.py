from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_metals_recommendation_change_authority_design.py"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-recommendation-change-authority-design-audit.yml"
DOC = ROOT / "docs" / "project_control" / "metals_recommendation_change_authority_design_v1.md"


def _load_module():
    spec = importlib.util.spec_from_file_location("recommendation_change_design", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_design_constants_are_native_and_nonlegacy():
    module = _load_module()
    assert module.EXPECTED_MODEL_ID == "uip-metals-native-trend-v1"
    assert module.EXPECTED_RECOMMENDATIONS == {"STRONG_BUY", "BUY", "HOLD", "REDUCE", "AVOID"}


def test_workflow_is_manual_only_and_read_only():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "environment: staging" in workflow
    assert "UIIP_DATABASE_URL" in workflow
    assert "audit_metals_rich_lineage.py" in workflow
    assert "audit_metals_recommendation_change_authority_design.py" in workflow
    assert "publication" not in workflow.lower() or "publication_staged" in workflow.lower()


def test_scope_document_forbids_vehicle_projection_and_production_authorization():
    doc = DOC.read_text(encoding="utf-8")
    assert "BENCHMARK_COMMODITY_ASSET_ONLY" in doc
    assert "commodity-to-vehicle recommendation projection" in doc
    assert "does not authorize a builder" in doc
    assert "central rich publisher remains manual/paused" in doc
