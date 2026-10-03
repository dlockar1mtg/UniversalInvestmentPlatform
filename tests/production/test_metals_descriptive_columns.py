from exchange.metals.adapter.uip_native import _descriptive_columns

BLOCK = {
    "descriptive": {
        "valuation": {"gap": 0.2, "state": "ABOVE_LONG_RUN_AVERAGE"},
        "trend": {"gap": -0.03, "state": "BELOW_TREND"},
        "historical_12m_returns": {"p10": -0.2, "p50": 0.05, "p90": 0.35, "samples": 240},
    }
}


def test_the_descriptive_block_becomes_flat_forecast_columns():
    assert _descriptive_columns(BLOCK) == {
        "valuation_gap_10y": 0.2,
        "valuation_state": "ABOVE_LONG_RUN_AVERAGE",
        "trend_gap_12m": -0.03,
        "trend_state": "BELOW_TREND",
        "historical_12m_return_p10": -0.2,
        "historical_12m_return_p50": 0.05,
        "historical_12m_return_p90": 0.35,
        "historical_12m_return_samples": 240,
    }


def test_missing_indicators_keep_the_same_columns_blank():
    # Every forecast row must carry the same keys, because the CSV header comes from the first row.
    for components in ({}, {"descriptive": None}, {"descriptive": {"valuation": None, "trend": None}}):
        columns = _descriptive_columns(components)
        assert set(columns) == set(_descriptive_columns(BLOCK))
        assert all(value == "" for value in columns.values())
