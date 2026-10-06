"""The crypto forecast tracking summary reaches the Crypto v2 pages as labeled context."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from foundation.presentation.crypto_forecast_tracking import apply_crypto_forecast_tracking

JS = (Path(__file__).resolve().parents[2] / "foundation" / "production" / "dashboard_assets" / "recommendation_ui.js").read_text(encoding="utf-8")


def _record(asset: str, v2: bool = True):
    return SimpleNamespace(domain_id="crypto", record_type="recommendation", asset_id=f"crypto:{asset}",
                           payload={"model_version": "crypto-v2"} if v2 else {})


def _artifact(tmp_path: Path) -> Path:
    folder = tmp_path / "forecast_tracking"
    folder.mkdir(parents=True)
    (folder / "forecast_tracking_summary.json").write_text(json.dumps({
        "generated_at_utc": "2026-10-06T12:00:00+00:00",
        "latest_price_date": "2026-10-05",
        "v4_7d": {"label": "Context only.", "status": "CONTEXT_ONLY", "holdout_evidence": {"final_holdout_rows": 60},
                  "forecasts": {"bitcoin": {"probability_up": 0.61, "origin_date": "2026-10-05", "target_date": "2026-10-12"}}},
        "scorecard": [
            {"model": "M39_CALIBRATED", "asset_id": "bitcoin", "horizon_days": 7, "forecasts_logged": 3, "forecasts_scored": 1},
            {"model": "M39_CALIBRATED", "asset_id": "solana", "horizon_days": 7, "forecasts_logged": 3, "forecasts_scored": 1},
        ],
    }), encoding="utf-8")
    return tmp_path


def test_tracking_is_attached_to_crypto_v2_records(tmp_path):
    btc, eth, sol, old = _record("bitcoin"), _record("ethereum"), _record("solana"), _record("xrp", v2=False)
    assert apply_crypto_forecast_tracking([btc, eth, sol, old], _artifact(tmp_path)) == 3

    assert btc.payload["model_short_term"]["forecast"]["probability_up"] == 0.61
    assert btc.payload["model_short_term"]["status"] == "CONTEXT_ONLY"
    assert [c["asset_id"] for c in btc.payload["model_forecast_scorecard"]] == ["bitcoin"]
    # ethereum had no forecast this run: the panel says so instead of disappearing
    assert eth.payload["model_short_term"]["forecast"] is None
    # altcoins get the legacy track record but no 7-day forecast
    assert "model_short_term" not in sol.payload and sol.payload["model_forecast_scorecard"]
    assert old.payload == {}


def test_missing_summary_changes_nothing(tmp_path):
    btc = _record("bitcoin")
    assert apply_crypto_forecast_tracking([btc], tmp_path) == 0
    assert btc.payload == {"model_version": "crypto-v2"}


def test_pages_show_the_context_and_track_record():
    for needle in ("function cvV2ShortTerm(p)", "${cvV2Projection(p)}${cvV2ShortTerm(p)}", "${cvV2LegacyPanel(p)}",
                   "function cvV2TrackRecord(p)", "It never changes the call.", "Track record so far"):
        assert needle in JS
