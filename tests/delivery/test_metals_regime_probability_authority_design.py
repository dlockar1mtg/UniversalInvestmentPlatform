from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_metals_regime_probability_authority_design.py"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-regime-probability-authority-design-audit.yml"
DOC = ROOT / "docs" / "project_control" / "metals_regime_probability_authority_design_v1.md"


def test_regime_probability_design_assets_exist():
    assert SCRIPT.is_file()
    assert WORKFLOW.is_file()
    assert DOC.is_file()


def test_regime_probability_design_workflow_is_manual_read_only_and_bounded():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "environment: staging" in text
    assert "scripts/audit_metals_rich_lineage.py" in text
    assert "scripts/audit_metals_regime_probability_authority_design.py" in text
    assert "native_model_component_v1/manifest.json" in text
    assert "native_risk_v1/manifest.json" in text
    assert "production-publication-cycle" not in text


def test_regime_probability_design_script_keeps_missing_semantics_explicit():
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"candidate_authority_boundary": "BENCHMARK_COMMODITY_ASSET_ONLY"' in text
    assert "canonical regime label taxonomy and exact label count" in text
    assert "probability normalization rule and fail-closed tolerance for sum-to-one" in text
    assert "descriptive score normalization versus calibrated probability" in text
    assert "explicit prohibition on copying restored legacy regime rows forward as fresh authority" in text
    assert "explicit prohibition on projecting vehicle-only risk authority into commodity probability without governed mapping" in text


def test_regime_probability_design_script_has_read_only_safety_flags():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'cur.execute("SET TRANSACTION READ ONLY")' in text
    assert '"postgres_write_performed": False' in text
    assert '"source_collection_performed": False' in text
    assert '"publication_staged": False' in text
    assert '"publication_activated": False' in text
    assert '"legacy_equivalent": False' in text
    assert "AUTHORIZE_UIP_NATIVE_METALS_REGIME_PROBABILITY_V1_DESIGN" in text


def test_regime_probability_design_doc_preserves_fail_closed_boundary():
    text = DOC.read_text(encoding="utf-8")
    assert "7 of 10 certified families" in text
    assert "historical evidence only" in text
    assert "does not authorize regime-probability production output" in text
    assert "fail closed" in text.lower()
    assert "statistical calibration" in text
