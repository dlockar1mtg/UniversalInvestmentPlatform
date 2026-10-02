import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "prepare_metals_vehicle_evidence_refresh.py"


def _module():
    spec = importlib.util.spec_from_file_location("prepare_metals_vehicle_evidence_refresh", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TEMPLATE = {
    "authority_id": "X",
    "minimum_distinct_sessions_required": 20,
    "vehicles": {"OLD": {"median_bid_ask_spread_bps": 9}},
    "spread_evidence_certified": True,
    "first_session": "2026-08-17",
    "last_session": "2026-09-14",
    "source_run_id": 1,
}


def _alpaca(**over):
    base = {
        "GLD": {"median_relative_bid_ask_spread_bps": 0.5, "distinct_session_count": 20,
                "first_session": "2026-09-03", "last_session": "2026-10-01"},
        "SGOL": {"median_relative_bid_ask_spread_bps": 2.3, "distinct_session_count": 21,
                 "first_session": "2026-09-02", "last_session": "2026-10-01"},
    }
    base.update(over)
    return {"per_ticker": base}


def test_spread_evidence_replaces_vehicles_and_keeps_governance_fields():
    module = _module()
    doc = module.spread_evidence(_alpaca(), TEMPLATE, ["GLD", "SGOL"], {"source_run_id": 99})
    assert doc["vehicles"] == {"GLD": {"median_bid_ask_spread_bps": 0.5}, "SGOL": {"median_bid_ask_spread_bps": 2.3}}
    assert doc["first_session"] == "2026-09-02" and doc["last_session"] == "2026-10-01"
    assert doc["authority_id"] == "X" and doc["source_run_id"] == 99 and doc["spread_evidence_certified"] is True
    assert TEMPLATE["vehicles"] == {"OLD": {"median_bid_ask_spread_bps": 9}}


def test_spread_evidence_refuses_missing_or_thin_vehicles():
    module = _module()
    with pytest.raises(ValueError, match="GLDM: no positive median"):
        module.spread_evidence(_alpaca(), TEMPLATE, ["GLD", "SGOL", "GLDM"], {})
    thin = {"median_relative_bid_ask_spread_bps": 0.5, "distinct_session_count": 5}
    with pytest.raises(ValueError, match="GLD: 5 sessions"):
        module.spread_evidence(_alpaca(GLD=thin), TEMPLATE, ["GLD"], {})


def test_commodity_state_takes_twelve_month_rows_and_fixes_the_doubled_prefix():
    module = _module()
    rows = [
        {"universal_asset_id": "metals:commodity:metals:commodity:gold", "tactical_horizon_months": "12",
         "recommendation": "buy", "tactical_state": "TACTICAL_POSITIVE_BUT_MIXED", "adjusted_expected_return": "0.069"},
        {"universal_asset_id": "metals:commodity:gold", "tactical_horizon_months": "36",
         "recommendation": "BUY", "tactical_state": "X", "adjusted_expected_return": "0.2"},
        {"universal_asset_id": "METALS:COMMODITY:SILVER", "tactical_horizon_months": "12",
         "recommendation": "STRONG_BUY", "tactical_state": "TACTICAL_SUPPORTIVE", "adjusted_expected_return": ""},
    ]
    state = module.commodity_state(rows)
    assert state["metals:commodity:gold"] == {
        "recommendation": "BUY", "tactical_state": "TACTICAL_POSITIVE_BUT_MIXED", "adjusted_expected_return_12m": 0.069,
    }
    assert state["metals:commodity:silver"]["adjusted_expected_return_12m"] is None


def test_commodity_state_refuses_duplicates_and_empty_input():
    module = _module()
    row = {"universal_asset_id": "metals:commodity:gold", "tactical_horizon_months": "12",
           "recommendation": "BUY", "tactical_state": "S", "adjusted_expected_return": "0.1"}
    with pytest.raises(ValueError, match="more than one"):
        module.commodity_state([row, dict(row)])
    with pytest.raises(ValueError, match="no 12-month"):
        module.commodity_state([])
