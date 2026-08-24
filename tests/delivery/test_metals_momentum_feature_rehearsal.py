from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_momentum_contract_is_fail_closed() -> None:
    text = (ROOT / "config" / "metals" / "momentum_feature_contract.json").read_text(encoding="utf-8")
    assert '"contract_id": "METALS-MOMENTUM-1"' in text
    assert '"momentum_feature_calculation_authorized": true' in text
    assert '"momentum_interpretation_policy_authorized": false' in text
    assert '"tactical_posture_authorized": false' in text
    assert '"cross_domain_rank_authorized": false' in text
    assert '"allocation_policy_authorized": false' in text
    assert '"automatic_execution_authorized": false' in text


def test_rehearsal_uses_read_only_history_and_no_posture() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_momentum_features.py").read_text(encoding="utf-8")
    assert 'BEGIN READ ONLY' in text
    assert 'metals_vehicle_observations' in text
    assert 'metals_market_benchmark_observations' in text
    assert 'METALS-MARKET-HISTORY-1' in text
    assert 'momentum_interpretation_policy_authorized": False' in text
    assert 'tactical_posture_authorized": False' in text
    assert 'REVIEW_METALS_MOMENTUM_FEATURE_BEHAVIOR' in text


def test_rehearsal_defines_expected_feature_family() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_momentum_features.py").read_text(encoding="utf-8")
    for name in (
        "return_1m_pct", "return_3m_pct", "return_6m_pct", "return_12m_pct",
        "distance_ma20_pct", "distance_ma50_pct", "distance_ma200_pct",
        "position_52w_range_pct", "current_drawdown_pct", "max_drawdown_52w_pct",
        "realized_volatility_3m_pct", "benchmark_relative_return_3m_pct",
        "momentum_acceleration_pct",
    ):
        assert name in text
