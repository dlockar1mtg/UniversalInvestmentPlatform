import csv
import json

from foundation.presentation import publication_model as pm
from foundation.presentation.publication_model import PresentationRecord

FIELDS = ["tcgplayer_product_id", "box_name", "release_date", "as_of", "price_date", "price", "price_source", "call", "note",
          "tier", "rank", "ranked_boxes", "tier_avg_return_12m", "tier_avg_net_return_12m", "tier_share_profitable", "tier_cases", "model_version"]


def _files(tmp_path):
    path = tmp_path / "precollector_v2_decisions.csv"
    rows = [{"tcgplayer_product_id": "60117", "box_name": "Return to Ravnica - Booster Box", "release_date": "2012-10-05", "as_of": "2026-10-06",
             "price_date": "2026-10-06", "price": "171.31", "price_source": "TCGCSV_DAILY", "call": "BUY", "note": "", "tier": "1", "rank": "8", "ranked_boxes": "85"},
            {"tcgplayer_product_id": "27262", "box_name": "Alpha Edition - Booster Box", "release_date": "1993-08-05", "as_of": "2026-10-06", "call": "NO_PRICE", "note": "NO_CURRENT_PRICE"},
            {"tcgplayer_product_id": "27303", "box_name": "Legends - Booster Box", "release_date": "1994-06-01", "as_of": "2026-10-06", "price": "9000", "call": "HOLD", "note": "VINTAGE_NO_MODEL_EDGE"}]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    path.with_suffix(".json").write_text(json.dumps({"as_of": "2026-10-06", "buy_tiers": [1, 2],
                                                     "tier_history": {"1": {"cases": 324, "avg_net_return": 0.092, "share_profitable": 0.73}}}))
    path.with_name("precollector_v2_history.json").write_text(json.dumps({"60117": [["2026-09", 168.0], ["2026-10", 171.31]]}))
    return path


def _records():
    pc = [PresentationRecord("recommendation", "mtg", f"PRE_COLLECTOR_V1|tcgplayer:{p}", f"PRE_COLLECTOR_V1|tcgplayer:{p}",
                             {"native_purchase_status": "TIER_1_TOP_QUARTILE", "native_rank": 4}) for p in ("60117", "27262", "27303", "999999")]
    return pc + [PresentationRecord("recommendation", "mtg", "SECRET_LAIR_V1_1|SL-X", "SECRET_LAIR_V1_1|SL-X", {"native_purchase_status": "WAIT_FOR_Q10_ENTRY"})]


def test_off_unless_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("UIP_MTG_PRECOLLECTOR_V2_PATH", str(_files(tmp_path)))
    monkeypatch.delenv("UIP_MTG_PRECOLLECTOR_V2_ENABLED", raising=False)
    records = _records()
    assert pm.apply_precollector_model_decisions(records) == 0 and all("model_call" not in r.payload for r in records)


def test_tiers_sit_beside_the_certified_authority(tmp_path, monkeypatch):
    monkeypatch.setenv("UIP_MTG_PRECOLLECTOR_V2_PATH", str(_files(tmp_path)))
    monkeypatch.setenv("UIP_MTG_PRECOLLECTOR_V2_ENABLED", "1")
    records = _records()
    assert pm.apply_precollector_model_decisions(records) == 4
    rtr, alpha, legends, unknown, lair = (r.payload for r in records)
    assert (rtr["model_call"], rtr["model_purchase_status"], rtr["model_tier"], rtr["model_rank"]) == ("BUY", "BUY_CANDIDATE_NOW", 1, 8)
    assert rtr["model_price_usd"] == 171.31 and rtr["model_tier_history"]["share_profitable"] == 0.73 and len(rtr["model_price_history"]) == 2
    assert alpha["model_call"] == "NO_PRICE" and legends["model_call"] == "HOLD" and legends["model_note"] == "VINTAGE_NO_MODEL_EDGE"
    assert unknown["model_call"] == "NO_PRICE" and unknown["model_note"] == "NOT_IN_PRICE_FEED"
    assert all(p["native_purchase_status"] == "TIER_1_TOP_QUARTILE" for p in (rtr, alpha, legends, unknown))   # certified fields untouched
    assert "model_call" not in lair
    for p in (rtr, alpha, legends, unknown):
        assert p["model_purchase_status"] == pm.PRECOLLECTOR_MODEL_STATUS[p["model_call"]]


def test_dashboard_renders_precollector_v2_pages():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[2] / "foundation" / "production" / "dashboard_assets" / "recommendation_ui.js").read_text(encoding="utf-8")
    for needle in ("function pcV2Detail(item)", "function pcV2Table(items)", "function pcV2Scorecard(items)",
                   '(p.model_version==="secret-lair-v2"||p.model_version==="precollector-v2"||p.model_version==="collector-v2")&&p.model_purchase_status',
                   "if(pcV2Decision(item)){pcV2RenderDetail(page,item);return;}", "This is history, not a forecast"):
        assert needle in js


def test_hold_calls_are_labelled_hold_not_no_price():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[2] / "foundation" / "production" / "dashboard_assets" / "recommendation_ui.js").read_text(encoding="utf-8")
    # Pre-Collector HOLD boxes have a price; the pill must not say NO PRICE (found on the live page, Oct 5)
    assert 'c==="HOLD"?"HOLD":"NO PRICE"' in js


def test_precollector_polish():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[2] / "foundation" / "production" / "dashboard_assets" / "recommendation_ui.js").read_text(encoding="utf-8")
    assert "function pcV2Change12(p)" in js and "Box price <small>past 12 mo</small>" in js
    assert '<strong class="pc-v2-years">' in js
    # call filters drop statuses that belong to other lanes (Secret Lair, Pre-Collector and Collector)
    assert js.count('if(i>0&&!labels[String(o.value||"").toUpperCase()]&&!o.selected)o.remove()') == 3
