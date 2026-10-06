"""Attach the crypto platform's forecast tracking to the Crypto v2 records.

The crypto production cycle writes forecast_tracking/forecast_tracking_summary.json into its run
evidence: the frozen V4 7-day forecast (context only) and the scorecard of the daily forecast log
(legacy M39/M42 forecasts and the V4 forecasts, scored as their dates arrive). This copies the
per-coin parts onto the Crypto v2 recommendation records. A missing or unreadable summary changes
nothing, so the publication never depends on it.
"""
from __future__ import annotations

import json
from pathlib import Path

SUMMARY = Path("forecast_tracking") / "forecast_tracking_summary.json"


def load_summary(crypto_artifact: Path) -> dict | None:
    candidates = [crypto_artifact / SUMMARY] + sorted(crypto_artifact.glob(f"**/{SUMMARY.name}"))
    for path in candidates:
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            return payload if isinstance(payload, dict) else None
    return None


def apply_crypto_forecast_tracking(records, crypto_artifact: Path) -> int:
    summary = load_summary(crypto_artifact)
    if not summary:
        return 0
    v4 = summary.get("v4_7d") or {}
    forecasts = v4.get("forecasts") or {}
    cards = [c for c in (summary.get("scorecard") or []) if isinstance(c, dict)]
    applied = 0
    for record in records:
        asset = str(record.asset_id or "")
        if record.domain_id != "crypto" or record.record_type != "recommendation" or not asset.startswith("crypto:"):
            continue
        if (record.payload or {}).get("model_version") != "crypto-v2":
            continue
        coin = asset.split(":", 1)[1]
        forecast = forecasts.get(coin)
        if forecast is not None or coin in ("bitcoin", "ethereum"):
            record.payload["model_short_term"] = {
                "status": "CONTEXT_ONLY",
                "label": v4.get("label"),
                "holdout_evidence": v4.get("holdout_evidence"),
                "forecast": forecast,
                "latest_price_date": summary.get("latest_price_date"),
                "generated_at_utc": summary.get("generated_at_utc"),
            }
        mine = [c for c in cards if c.get("asset_id") == coin]
        if mine:
            record.payload["model_forecast_scorecard"] = mine
        applied += 1
    return applied
