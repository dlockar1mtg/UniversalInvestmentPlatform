from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_price_history_read_binding_design_contract_exists() -> None:
    path = ROOT / "config" / "presentation" / "metals_price_history_read_binding_design.json"
    assert path.exists()


def test_price_history_design_requires_durable_export_boundary() -> None:
    text = (ROOT / "scripts" / "verify_metals_price_history_read_binding_design.py").read_text(encoding="utf-8")
    assert "METALS-PRICE-HISTORY-READ-BINDING-DESIGN-1" in text
    assert "VERSIONED_EXPORT_PACKAGE_REQUIRED" in text
    assert '"direct_native_query_prohibited": True' in text
    assert '"versioned_export_package_required": True' in text
    assert "metals_vehicle_observations" in text
    assert "metals_market_benchmark_observations" in text


def test_price_history_design_preserves_governance_boundaries() -> None:
    text = (ROOT / "scripts" / "verify_metals_price_history_read_binding_design.py").read_text(encoding="utf-8")
    assert '"export_execution_authorized": False' in text
    assert '"presentation_activation_authorized": False' in text
    assert '"production_database_write_executed": False' in text
    assert '"tactical_posture_authorized": False' in text
    assert '"cross_domain_rank_authorized": False' in text
    assert '"allocation_policy_authorized": False' in text
    assert '"automatic_execution_authorized": False' in text
