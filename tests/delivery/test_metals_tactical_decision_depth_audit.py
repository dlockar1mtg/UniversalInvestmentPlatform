from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_metals_tactical_depth_audit_is_read_only_and_covers_decision_layers():
    source = read("scripts/audit_metals_tactical_decision_depth.py")
    assert "read_only=True" in source
    assert "forecast_horizon_coverage" in source
    assert "forecast_asset_coverage" in source
    assert "recommendation_asset_coverage" in source
    assert "risk_metric_coverage" in source
    assert '"strategic_thesis"' in source
    assert '"medium_term_opportunity"' in source
    assert '"momentum_regime"' in source
    assert '"tactical_posture"' in source
    assert '"current_value_and_history"' in source
    assert "UPDATE " not in source
    assert "INSERT " not in source
    assert "DELETE " not in source
