import csv
import json
from pathlib import Path

from foundation.presentation import publication_model as pm
from foundation.presentation.mtg_secret_lair_v2_projection import REQUIRED_COLUMNS
from foundation.presentation.publication_model import PresentationRecord
from foundation.production.portfolio_enrichment import _recommendation

ROOT = Path(__file__).resolve().parents[2]


def _decisions(tmp_path):
    path = tmp_path / "secret_lair_v2_decisions.csv"
    rows = []
    for product, call, gap, net, rank in (("SL-A", "BUY", "0.2", "0.08", "1"), ("SL-B", "WAIT", "0.01", "-0.02", "2")):
        row = {c: "" for c in REQUIRED_COLUMNS}
        row.update(secret_lair_id=product, as_of="2026-10-05", market_price="50", gap=gap, expected_net_return_6m=net, call=call, rank=rank, ranked_products="2")
        rows.append(row)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REQUIRED_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    path.with_suffix(".json").write_text(json.dumps({"as_of": "2026-10-05", "buy_gap": 0.10}))
    return path


def _records():
    sl = [PresentationRecord("recommendation", "mtg", f"SECRET_LAIR_V1_1|{x}", f"SECRET_LAIR_V1_1|{x}", {"native_purchase_status": "WAIT_FOR_Q10_ENTRY", "native_rank": 7})
          for x in ("SL-A", "SL-B", "SL-GONE")]
    return sl + [PresentationRecord("asset", "mtg", "SECRET_LAIR_V1_1|SL-A", "SECRET_LAIR_V1_1|SL-A", {}),
                 PresentationRecord("recommendation", "mtg", "COLLECTOR_V1|X", "COLLECTOR_V1|X", {"native_purchase_status": "WATCHLIST"})]


def test_off_unless_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("UIP_MTG_SECRET_LAIR_V2_PATH", str(_decisions(tmp_path)))
    monkeypatch.delenv("UIP_MTG_SECRET_LAIR_V2_ENABLED", raising=False)
    records = _records()
    assert pm.apply_secret_lair_model_decisions(records) == 0
    assert all("model_call" not in r.payload for r in records)


def test_model_decisions_sit_beside_the_certified_authority(tmp_path, monkeypatch):
    monkeypatch.setenv("UIP_MTG_SECRET_LAIR_V2_PATH", str(_decisions(tmp_path)))
    monkeypatch.setenv("UIP_MTG_SECRET_LAIR_V2_ENABLED", "1")
    records = _records()
    assert pm.apply_secret_lair_model_decisions(records) == 3
    a, b, gone, asset, collector = records
    assert (a.payload["model_call"], a.payload["model_purchase_status"], a.payload["model_rank"]) == ("BUY", "BUY_CANDIDATE_NOW", 1)
    assert b.payload["model_purchase_status"] == "WAIT_FOR_LISTING_DISCOUNT"
    # the deals table reads these straight from the catalog
    assert (a.payload["model_gap"], a.payload["model_expected_net_return_6m"]) == (0.2, 0.08)
    assert gone.payload["model_gap"] is None and gone.payload["model_buy_price_usd"] is None
    assert gone.payload["model_call"] == "NO_PRICE" and gone.payload["model_note"] == "NOT_IN_DAILY_PRICE_FEED"
    # the certified native authority is preserved, as the MTG parity contract requires
    assert all(r.payload["native_purchase_status"] == "WAIT_FOR_Q10_ENTRY" and r.payload["native_rank"] == 7 for r in (a, b, gone))
    assert asset.payload == {} and "model_call" not in collector.payload
    # every model status agrees with its model call
    for r in (a, b, gone):
        assert r.payload["model_purchase_status"] == pm.SECRET_LAIR_MODEL_STATUS[r.payload["model_call"]]


def test_portfolio_prefers_the_model_decision():
    assert _recommendation({"native_purchase_status": "WAIT_FOR_Q10_ENTRY", "model_version": "secret-lair-v2", "model_purchase_status": "BUY_CANDIDATE_NOW"}) == ("BUY_CANDIDATE_NOW", "model_purchase_status")
    assert _recommendation({"native_purchase_status": "WATCHLIST"}) == ("WATCHLIST", "native_purchase_status")


def test_dashboard_reads_status_and_rank_through_the_model_decision():
    js = (ROOT / "foundation" / "production" / "dashboard_assets" / "recommendation_ui.js").read_text(encoding="utf-8")
    assert "function mtgModelDecision(item)" in js
    assert "mtgModelDecision(item)?mtgModelDecision(item).model_purchase_status" in js
    assert "const model=mtgModelDecision(item);" in js
    assert "function slV2Ranked(items){return items.some(i=>Boolean(mtgModelDecision(i)))}" in js


def test_dashboard_deals_table_reads_catalog_fields():
    js = (ROOT / "foundation" / "production" / "dashboard_assets" / "recommendation_ui.js").read_text(encoding="utf-8")
    for needle in ("function slV2Table(items)", "function slV2Apply(items)", "p.model_expected_net_return_6m", "bindSlV2Controls(page)", "slV2LaneOn = slV2Ranked("):
        assert needle in js
