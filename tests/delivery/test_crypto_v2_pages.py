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

def test_home_page_uses_crypto_v2_cards():
    # the Recommendations home showed the old 3-year forecasts unlabeled (found Oct 6)
    for needle in ("${cvV2On(crypto)?`<div class=\"cv-v2-grid\">${cvV2Order(crypto).map(cvV2Card).join(\"\")}</div>${cvV2HomeExplainer()}`",
                   "bindDomainButtons(page);if(cvV2On(crypto))bindCvV2(page)", "function cvV2HomeExplainer()", 'lens="Crypto v2"'):
        assert needle in JS


def test_collector_no_call_reasons():
    for needle in ('p.model_note==="NOT_YET_RELEASED"', "function clV2Pts(v)", "${clV2Pts(rec.buy_quarter_edge)} vs all boxes"):
        assert needle in JS
