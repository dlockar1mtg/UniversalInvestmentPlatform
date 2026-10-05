from pathlib import Path

JS = (Path(__file__).resolve().parents[2] / "foundation" / "production" / "dashboard_assets" / "recommendation_ui.js").read_text(encoding="utf-8")


def test_crypto_v2_pages_are_wired():
    for needle in ("function cvV2List(all,filtered)", "function cvV2Detail(item)", "function cvV2ZoneTable(p)",
                   "if(cvV2On(all)){page.innerHTML=cvV2List(all,filtered);bindDomainControls(page,0);bindCvV2(page);return;}",
                   'if(cvV2Decision(item)){cvV2RenderDetail(node("recommendations"),item);return;}'):
        assert needle in JS


def test_crypto_v2_pages_state_their_limits():
    # timing guidance, not forecasts; alts get no call; halving is context only
    for needle in ("Timing guidance, not price forecasts.", "so the model makes no call", "this never changes the call by itself"):
        assert needle in JS
