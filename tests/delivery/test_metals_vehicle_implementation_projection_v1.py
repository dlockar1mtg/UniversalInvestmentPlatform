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


def test_projection_carries_governed_identity_cost_and_score_evidence():
    records = _records()
    by_ticker = {r.payload["ticker"]: r.payload for r in records}

    assert by_ticker["GLD"]["vehicle_id"] == "metals:vehicle:GLD"
    assert by_ticker["GLD"]["vehicle_type"] == "physical_backed_etf"
    assert by_ticker["GLD"]["expense_ratio_pct"] == 0.40
    assert by_ticker["GLD"]["certified_implementation_score"] == 85.48544649732895

    assert by_ticker["COPX"]["vehicle_type"] == "miners_etf"
    assert by_ticker["CPER"]["vehicle_type"] == "futures_fund"
    assert by_ticker["URA"]["vehicle_type"] == "thematic_equity_etf"
    assert by_ticker["PPLT"]["certified_implementation_score"] is None


def test_projection_preserves_non_authorizations_and_paused_cron():
    for record in _records():
        payload = record.payload
        assert payload["ranking_may_not_override_commodity_recommendation"] is True
        assert payload["automatic_execution_authorized"] is False
        assert payload["portfolio_allocation_authorized"] is False
        assert payload["position_sizing_authorized"] is False
        assert payload["central_publication_cron_restoration_authorized"] is False
