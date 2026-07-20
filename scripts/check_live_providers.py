"""Opt-in connectivity check for configured live providers."""

import json
import importlib.util
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "foundation" / "production" / "providers.py"
SPEC = importlib.util.spec_from_file_location("uiip_live_providers", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load provider module")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
AlphaVantageProvider = MODULE.AlphaVantageProvider
FREDProvider = MODULE.FREDProvider
ProviderError = MODULE.ProviderError

try:
    quote = AlphaVantageProvider().quote(os.getenv("UIIP_ALPHA_VANTAGE_TEST_SYMBOL", "SPY"))
    observation = FREDProvider().latest(os.getenv("UIIP_FRED_TEST_SERIES", "MORTGAGE30US"))
except (ValueError, ProviderError) as exc:
    print(json.dumps({"status": "FAILED", "error": str(exc)}, indent=2))
    raise SystemExit(1)

print(json.dumps({
    "status": "PASSED",
    "alpha_vantage": {"symbol": quote.symbol, "price": str(quote.price), "date": quote.trading_date.isoformat()},
    "fred": {"series_id": observation.series_id, "value": str(observation.value), "date": observation.observation_date.isoformat()},
}, indent=2, sort_keys=True))
