import csv
import json
from pathlib import Path

from foundation.presentation import publication_model as pm
from foundation.presentation.publication_model import PresentationRecord

FIELDS = ["tcgplayer_product_id", "box_name", "as_of", "market_price", "low_price", "direct_low_price", "months_since_release",
          "in_sweet_spot", "trend_6m", "expected_return_6m", "expected_net_return_6m", "call", "rank", "ranked_products", "quarter",
          "calibrated_net_return_6m", "calibrated_net_p10_6m", "calibrated_net_p90_6m", "calibrated_share_profitable", "model_version"]
WALK = {"test_months": 12, "first_test_month": "2025-02", "last_test_month": "2026-01", "status": "PROVISIONAL",
        "quarters": {"1": {"cases": 126, "avg_net_return": 0.1472, "p10_net_return": -0.1369, "p50_net_return": 0.1494,
                           "p90_net_return": 0.3983, "share_profitable": 0.7222, "avg_predicted_net_return": 0.1548}},
        "all_boxes": {"cases": 483, "avg_net_return": 0.1007}, "recent": {"test_months": 6, "buy_quarter_edge": -0.0095}}


def _files(tmp_path):
    path = tmp_path / "collector_v2_decisions.csv"
    rows = [{"tcgplayer_product_id": "618893", "box_name": "Final Fantasy Collector Booster Box", "as_of": "2026-10-06", "market_price": "1508.77",
             "months_since_release": "15.6", "in_sweet_spot": "1", "trend_6m": "0.337", "expected_return_6m": "0.3387",
             "expected_net_return_6m": "0.1647", "call": "BUY", "rank": "1", "ranked_products": "47", "quarter": "1",
             "calibrated_net_return_6m": "0.1472", "calibrated_net_p10_6m": "-0.1369", "calibrated_net_p90_6m": "0.3983",
             "calibrated_share_profitable": "0.7222", "model_version": "collector-v2"},
            {"tcgplayer_product_id": "208279", "box_name": "Ikoria Collector Booster Display", "as_of": "2026-10-06", "market_price": "561.43",
             "months_since_release": "76.7", "in_sweet_spot": "0", "trend_6m": "0.183", "expected_return_6m": "0.2226",
             "expected_net_return_6m": "0.0636", "call": "HOLD", "rank": "27", "ranked_products": "47", "quarter": "3", "model_version": "collector-v2"},
            {"tcgplayer_product_id": "700001", "box_name": "New box", "as_of": "2026-10-06", "market_price": "300", "call": "NO_PRICE", "model_version": "collector-v2"}]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    path.with_suffix(".json").write_text(json.dumps({"as_of": "2026-10-06", "walk_forward": WALK}))
    path.with_name("collector_v2_history.json").write_text(json.dumps({"618893": [["2026-09", 1450.0], ["2026-10", 1508.77]]}))
    return path


def _records():
    ids = ("618893", "208279", "700001", "999999")
    co = [PresentationRecord("recommendation", "mtg", f"COLLECTOR_V1|MTG-CANON-TCGPLAYER-{p}", f"COLLECTOR_V1|MTG-CANON-TCGPLAYER-{p}",
                             {"native_purchase_status": "TIER_1_TOP_QUARTILE", "native_rank": 4}) for p in ids]
    return co + [PresentationRecord("recommendation", "mtg", "PRE_COLLECTOR_V1|tcgplayer:60117", "PRE_COLLECTOR_V1|tcgplayer:60117", {"native_purchase_status": "X"})]


def test_off_unless_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("UIP_MTG_COLLECTOR_V2_PATH", str(_files(tmp_path)))
    monkeypatch.delenv("UIP_MTG_COLLECTOR_V2_ENABLED", raising=False)
    records = _records()
    assert pm.apply_collector_model_decisions(records) == 0 and all("model_call" not in r.payload for r in records)


def test_decisions_sit_beside_the_certified_authority(tmp_path, monkeypatch):
    monkeypatch.setenv("UIP_MTG_COLLECTOR_V2_PATH", str(_files(tmp_path)))
    monkeypatch.setenv("UIP_MTG_COLLECTOR_V2_ENABLED", "1")
    records = _records()
    assert pm.apply_collector_model_decisions(records) == 4
    ff, ikoria, new, unknown, pre = (r.payload for r in records)
    assert (ff["model_call"], ff["model_purchase_status"], ff["model_rank"], ff["model_quarter"]) == ("BUY", "BUY_CANDIDATE_NOW", 1, 1)
    # the expected return shown is the tested quarter result, not the raw regression number
    assert ff["model_expected_net_return_6m"] == 0.1472 and ff["model_raw_expected_net_return_6m"] == 0.1647
    assert (ff["model_net_p10_6m"], ff["model_net_p90_6m"], ff["model_share_profitable_6m"]) == (-0.1369, 0.3983, 0.7222)
    assert ff["model_validation_status"] == "PROVISIONAL" and ff["model_walk_forward"]["test_months"] == 12
    assert ff["model_in_sweet_spot"] is True and ff["model_price_usd"] == 1508.77 and len(ff["model_price_history"]) == 2
    assert ikoria["model_call"] == "HOLD" and ikoria["model_expected_net_return_6m"] is None and ikoria["model_validation_status"] == "NOT_VALIDATED"
    assert new["model_call"] == "NO_PRICE" and new["model_note"] == "NO_RELEASE_DATE"
    assert unknown["model_call"] == "NO_PRICE" and unknown["model_note"] == "NOT_IN_PRICE_FEED"
    assert all(p["native_purchase_status"] == "TIER_1_TOP_QUARTILE" for p in (ff, ikoria, new, unknown))  # certified fields untouched
    assert "model_call" not in pre
    for p in (ff, ikoria, new, unknown):
        assert p["model_purchase_status"] == pm.COLLECTOR_MODEL_STATUS[p["model_call"]]


def test_product_id_from_collector_asset_ids():
    assert pm._collector_product_id("COLLECTOR_V1|MTG-CANON-TCGPLAYER-618893") == "618893"
    assert pm._collector_product_id("COLLECTOR_V1|tcgplayer:562122") == "562122"
    assert pm._collector_product_id("COLLECTOR_V1|something-else") == ""


def test_dashboard_renders_collector_v2_pages():
    js = (Path(__file__).resolve().parents[2] / "foundation" / "production" / "dashboard_assets" / "recommendation_ui.js").read_text(encoding="utf-8")
    for needle in ("function clV2Detail(item)", "function clV2Table(items)", "function clV2Scorecard(items)", "function clV2QuarterTable(w,mine)",
                   'p.model_version==="precollector-v2"||p.model_version==="collector-v2")&&p.model_purchase_status',
                   "if(clV2Decision(item)){clV2RenderDetail(page,item);return;}", "if(mtgLane===\"collector\"&&clV2LaneOn){bindClV2(page,visible);}",
                   "mtgLane===\"collector\"&&clV2LaneOn?clV2Table(visible):", r"not the model\u2019s raw estimate"):
        assert needle in js, needle
