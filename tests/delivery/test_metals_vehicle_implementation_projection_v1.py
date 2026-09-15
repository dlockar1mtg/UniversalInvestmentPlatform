from pathlib import Path

from foundation.presentation.metals_vehicle_implementation_projection import (
    ONLY_LABEL,
    PREFERRED_LABEL,
    build_metals_vehicle_implementation_records,
)

ROOT = Path(__file__).resolve().parents[2]


def _records():
    return build_metals_vehicle_implementation_records(ROOT)


def test_projection_emits_exact_ranked_vehicle_universe():
    records = _records()
    assert len(records) == 10
    assert {record.record_type for record in records} == {"metals_vehicle_implementation"}
    assert {record.domain_id for record in records} == {"metals"}
    assert {record.payload["ticker"] for record in records} == {
        "GLD", "IAU", "SGOL", "SLV", "SIVR", "PPLT", "CPER", "COPX", "URA", "URNM"
    }
    assert all(record.asset_id.startswith("metals:commodity:") for record in records)


def test_projection_preserves_certified_order_and_labels():
    records = _records()
    by_commodity = {}
    for record in records:
        by_commodity.setdefault(record.asset_id, []).append(record)
    for rows in by_commodity.values():
        rows.sort(key=lambda item: item.payload["certified_rank_within_commodity"])

    assert [r.payload["ticker"] for r in by_commodity["metals:commodity:gold"]] == ["GLD", "SGOL", "IAU"]
    assert [r.payload["ticker"] for r in by_commodity["metals:commodity:silver"]] == ["SLV", "SIVR"]
    assert [r.payload["ticker"] for r in by_commodity["metals:commodity:platinum"]] == ["PPLT"]
    assert [r.payload["ticker"] for r in by_commodity["metals:commodity:copper"]] == ["COPX", "CPER"]
    assert [r.payload["ticker"] for r in by_commodity["metals:commodity:uranium"]] == ["URA", "URNM"]

    labels = {r.payload["ticker"]: r.payload["presentation_label"] for r in records}
    assert labels["GLD"] == PREFERRED_LABEL
    assert labels["COPX"] == PREFERRED_LABEL
    assert labels["URA"] == PREFERRED_LABEL
    assert labels["PPLT"] == ONLY_LABEL
    assert labels["SLV"] is None
    assert labels["SIVR"] is None


def test_silver_remains_defensive_and_preferred_label_is_suppressed():
    silver = [r for r in _records() if r.asset_id == "metals:commodity:silver"]
    assert len(silver) == 2
    assert all(r.payload["upstream_recommendation"] == "REDUCE" for r in silver)
    assert all(r.payload["upstream_tactical_state"] == "TACTICAL_DEFENSIVE" for r in silver)
    assert all(r.payload["preferred_buy_label_suppressed"] is True for r in silver)
    assert all(r.payload["presentation_label"] is None for r in silver)


def test_projection_carries_governed_identity_cost_score_and_component_evidence():
    by_ticker = {r.payload["ticker"]: r.payload for r in _records()}
    gld = by_ticker["GLD"]
    assert gld["vehicle_id"] == "metals:vehicle:GLD"
    assert gld["vehicle_type"] == "physical_backed_etf"
    assert gld["expense_ratio_pct"] == 0.40
    assert gld["certified_implementation_score"] == 85.48544649732895
    assert gld["ranking_component_evidence_authority_id"] == "UIP_NATIVE_METALS_VEHICLE_RANKING_COMPONENT_EVIDENCE_V1"
    assert gld["ranking_weights"] == {
        "exposure_fidelity": 0.35,
        "cost_efficiency": 0.25,
        "liquidity_implementation_friction": 0.25,
        "risk_efficiency": 0.15,
    }
    assert gld["exposure_fidelity_score"] == 100.0
    assert gld["cost_efficiency_score"] == 42.5
    assert gld["liquidity_implementation_friction_score"] == 100.0
    assert gld["risk_efficiency_score"] == 99.06964331552635
    assert gld["average_dollar_volume_usd"] == 3758288420.8526664
    assert gld["bid_ask_spread_bps"] == 0.4896385164486847
    assert gld["volatility"] == 0.29271263
    assert gld["maximum_drawdown_magnitude"] == 0.26404518

    assert by_ticker["COPX"]["vehicle_type"] == "miners_etf"
    assert by_ticker["CPER"]["vehicle_type"] == "futures_fund"
    assert by_ticker["URA"]["vehicle_type"] == "thematic_equity_etf"

    pplt = by_ticker["PPLT"]
    assert pplt["certified_implementation_score"] is None
    assert pplt["cost_efficiency_score"] is None
    assert pplt["liquidity_implementation_friction_score"] is None
    assert pplt["risk_efficiency_score"] is None
    assert pplt["average_dollar_volume_usd"] == 41783537.960130624
    assert pplt["bid_ask_spread_bps"] == 6.06428194019866


def test_projection_preserves_non_authorizations_and_paused_cron():
    for record in _records():
        payload = record.payload
        assert payload["ranking_may_not_override_commodity_recommendation"] is True
        assert payload["automatic_execution_authorized"] is False
        assert payload["portfolio_allocation_authorized"] is False
        assert payload["position_sizing_authorized"] is False
        assert payload["central_publication_cron_restoration_authorized"] is False
