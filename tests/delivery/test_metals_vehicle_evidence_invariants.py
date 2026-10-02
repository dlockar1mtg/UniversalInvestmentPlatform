"""Rules any refreshed Metals vehicle evidence must satisfy.

These replace tests that pinned one dated snapshot (the August 2026 order, source
run ids, spreads and recommendation states). Every evidence refresh changes those
values, so they are checked here as invariants instead: one ranking binds the three
files, every registered vehicle is covered, orders follow scores, preferred labels
obey the published rule, and the real projection accepts the committed files.
"""
import json
from pathlib import Path

from foundation.presentation.metals_vehicle_implementation_projection import (
    build_metals_vehicle_implementation_records,
)

ROOT = Path(__file__).resolve().parents[2]
PRESENTATION = ROOT / "config" / "presentation"
PREFERRED_LABEL = "PREFERRED_IMPLEMENTATION_CANDIDATE"
ONLY_LABEL = "ONLY_REGISTERED_IMPLEMENTATION"


def _read(name):
    return json.loads((PRESENTATION / name).read_text(encoding="utf-8-sig"))


RANKING = _read("metals_vehicle_ranking_evidence_v1.json")
COMPONENT = _read("metals_vehicle_ranking_component_evidence_v1.json")
AUTH = _read("metals_vehicle_presentation_authorization_v1.json")
SPREAD = _read("metals_vehicle_spread_evidence_v1.json")
CONFIG = _read("metals_vehicle_ranking_v1.json")
REGISTERED = {
    row["ticker"]: row
    for row in json.loads((ROOT / "config" / "metals" / "vehicles.json").read_text(encoding="utf-8-sig"))["vehicles"]
    if row.get("enabled", True) and row.get("role") != "reserve"
}
# A newly registered fund is not ranked until its first evidence refresh.
RANKED = {ticker for group in RANKING["groups"] for ticker in group["certified_order"]}


def test_the_three_files_are_bound_to_one_ranking_and_methodology():
    assert RANKING["ranking_methodology_version"] == COMPONENT["ranking_methodology_version"] == CONFIG["methodology_version"]
    assert RANKING["ranking_authority_id"] == COMPONENT["ranking_authority_id"] == CONFIG["authority_id"]
    assert RANKING["source_artifact_digest"] == COMPONENT["source_artifact_digest"] == AUTH["ranking_source_artifact_digest"]
    assert str(RANKING["source_artifact_digest"]).startswith("sha256:")
    assert AUTH["ranking_evidence_authority_id"] == RANKING["authority_id"]
    assert RANKING["weights"] == COMPONENT["weights"] == CONFIG["weights"]


def test_every_ranked_vehicle_is_registered_and_appears_once_under_its_own_metal():
    seen = {}
    for group in RANKING["groups"]:
        for ticker in group["certified_order"]:
            assert ticker not in seen, f"{ticker} is ranked twice"
            seen[ticker] = group["commodity_id"]
    assert set(seen) <= set(REGISTERED)
    for ticker, commodity_id in seen.items():
        assert REGISTERED[ticker]["underlying_asset_id"] == commodity_id
    assert RANKING["registered_vehicle_count"] == len(seen)
    assert RANKING["commodity_group_count"] == len(RANKING["groups"])


def test_orders_agree_across_files_and_follow_the_scores():
    components = {group["commodity_id"]: group for group in COMPONENT["groups"]}
    authorizations = {item["commodity_id"]: item for item in AUTH["commodities"]}
    assert set(components) == set(authorizations) == {group["commodity_id"] for group in RANKING["groups"]}
    for group in RANKING["groups"]:
        commodity_id = group["commodity_id"]
        order = group["certified_order"]
        assert components[commodity_id]["certified_order"] == order
        assert authorizations[commodity_id]["certified_vehicle_order"] == order
        assert [row["ticker"] for row in components[commodity_id]["vehicles"]] == order
        if len(order) == 1:
            assert group["certified_leader"] is None
            continue
        assert group["certified_leader"] == order[0]
        rows = {row["ticker"]: row for row in components[commodity_id]["vehicles"]}
        passed = [rows[ticker].get("liquidity_floor_passed", True) is not False for ticker in order]
        # Vehicles that clear the liquidity floor come first; within each block, by score.
        assert passed == sorted(passed, reverse=True)
        for block in (True, False):
            scores = [group["scores"][ticker] for ticker, ok in zip(order, passed) if ok is block]
            assert scores == sorted(scores, reverse=True)


def test_preferred_labels_follow_the_published_actionability_rule():
    gate = AUTH["actionability_gate"]
    recommendations = set(gate["preferred_label_requires_recommendation"])
    tactical_states = set(gate["preferred_label_requires_tactical_state"])
    leaders = {group["commodity_id"]: group["certified_leader"] for group in RANKING["groups"]}
    for item in AUTH["commodities"]:
        if len(item["certified_vehicle_order"]) == 1:
            assert item["authorized_label"] == ONLY_LABEL
            assert item["authorized_preferred_vehicle"] is None
            continue
        if item["authorized_preferred_vehicle"] is None:
            assert item["authorized_label"] != PREFERRED_LABEL
            continue
        assert item["recommendation"] in recommendations
        assert item["tactical_state"] in tactical_states
        assert item["authorized_preferred_vehicle"] == leaders[item["commodity_id"]]
        assert item["authorized_label"] == PREFERRED_LABEL


def test_spread_evidence_is_certified_for_every_registered_vehicle():
    assert SPREAD["spread_evidence_certified"] is True
    assert RANKED <= set(SPREAD["vehicles"]) <= set(REGISTERED)
    assert all(float(row["median_bid_ask_spread_bps"]) > 0 for row in SPREAD["vehicles"].values())
    assert str(SPREAD["first_session"]) <= str(SPREAD["last_session"])


def test_the_projection_accepts_the_committed_evidence():
    records = build_metals_vehicle_implementation_records(ROOT)
    assert len(records) == len(RANKED)
    tickers = [record.payload["ticker"] for record in records]
    assert sorted(tickers) == sorted(RANKED)
    for record in records:
        assert int(record.payload["certified_rank_within_commodity"]) >= 1
        assert record.payload.get("presentation_label") in (None, PREFERRED_LABEL, ONLY_LABEL)
