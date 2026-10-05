import csv
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from foundation.presentation import crypto_v2_model as cv  # noqa: E402

spec = importlib.util.spec_from_file_location("fetch_crypto", ROOT / "scripts" / "fetch_crypto_monthly_closes.py")
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)


class Rec:
    def __init__(self, asset_id, record_type="recommendation"):
        self.asset_id, self.record_type, self.payload = asset_id, record_type, {"recommendation": "buy"}


def _months(n, start=(2018, 1)):
    out = []
    for i in range(n):
        y, m = divmod(start[1] - 1 + i, 12)
        out.append(f"{start[0] + y:04d}-{m + 1:02d}")
    return out


def _write(tmp_path, series):
    path = tmp_path / "crypto_monthly_closes.csv"
    with path.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=["asset", "month", "close", "source", "updated_utc"])
        w.writeheader()
        for asset, (months, prices) in series.items():
            for m, p in zip(months, prices):
                w.writerow({"asset": asset, "month": m, "close": p, "source": "TEST", "updated_utc": "2026-10-05T19:30:00Z"})
    return path


def _flat_then(last):            # 59 months at 100, then a final price: ratio = last / avg of last 48
    return _months(60), [100.0] * 59 + [last]


def test_calls_follow_the_ratio_thresholds(tmp_path, monkeypatch):
    for last, call in ((50.0, "ACCUMULATE"), (150.0, "STEADY"), (300.0, "PAUSE")):
        path = _write(tmp_path, {"bitcoin": _flat_then(last), "ethereum": _flat_then(100.0)})
        monkeypatch.setenv("UIP_CRYPTO_V2_ENABLED", "1")
        monkeypatch.setenv("UIP_CRYPTO_V2_PATH", str(path))
        recs = [Rec("crypto:bitcoin")]
        assert cv.apply_crypto_model_decisions(recs) == 1
        p = recs[0].payload
        assert p["model_call"] == call and p["model_purchase_status"] == cv.STATUS[call] and p["recommendation"] == "buy"
        assert p["model_role"] == "CORE" and p["model_robinhood_tradable"] is True and "OVER_TWO" in p["model_zone_history"]


def test_alts_get_no_call_and_a_record_against_bitcoin(tmp_path, monkeypatch):
    months = _months(72)
    path = _write(tmp_path, {"bitcoin": (months, [100 * 1.02 ** i for i in range(72)]),
                             "solana": (months, [100 * 1.01 ** i for i in range(72)])})
    monkeypatch.setenv("UIP_CRYPTO_V2_ENABLED", "1")
    monkeypatch.setenv("UIP_CRYPTO_V2_PATH", str(path))
    recs = [Rec("crypto:solana"), Rec("crypto:avalanche"), Rec("stock:SPY")]
    assert cv.apply_crypto_model_decisions(recs) == 2
    sol, avax, spy = (r.payload for r in recs)
    assert sol["model_call"] == "NO_CALL" and sol["model_role"] == "CONTEXTUAL"
    assert sol["model_vs_btc"]["share_beat_btc"] == 0 and sol["model_vs_btc"]["cases"] == 60
    assert avax["model_call"] == "NO_PRICE" and "model_call" not in spy


def test_short_history_gets_no_call(tmp_path, monkeypatch):
    path = _write(tmp_path, {"ethereum": (_months(30), [100.0] * 30)})
    monkeypatch.setenv("UIP_CRYPTO_V2_ENABLED", "1")
    monkeypatch.setenv("UIP_CRYPTO_V2_PATH", str(path))
    recs = [Rec("crypto:ethereum")]
    cv.apply_crypto_model_decisions(recs)
    assert recs[0].payload["model_call"] == "NO_CALL" and recs[0].payload["model_ratio_48m"] is None


def test_off_unless_enabled(tmp_path, monkeypatch):
    monkeypatch.delenv("UIP_CRYPTO_V2_ENABLED", raising=False)
    recs = [Rec("crypto:bitcoin")]
    assert cv.apply_crypto_model_decisions(recs) == 0 and "model_call" not in recs[0].payload


def test_halving_context_for_bitcoin(tmp_path):
    path = _write(tmp_path, {"bitcoin": (_months(60, (2022, 1)), [100.0] * 60)})
    closes = cv.load_closes(path)
    closes.pop("__updated__")
    s = cv.score_asset("bitcoin", closes)
    assert s["last_halving"] == "2024-04" and s["months_since_halving"] == 32     # 2026-12 is 32 months after 2024-04


def test_fetcher_keeps_months_kraken_no_longer_returns(tmp_path):
    out = tmp_path / "closes.csv"
    out.write_text("asset,month,close,source,updated_utc\nbitcoin,2013-10,123.8,KRAKEN_WEEKLY_OHLC,old\n")
    # two weekly candles in Sept 2026 (the later one wins) and one in Oct 2026
    candles = [[1788393600, 0, 0, 0, "60000"], [1788998400, 0, 0, 0, "61000"], [1790812800, 0, 0, 0, "85755"]]
    fake = lambda url: {"error": [], "result": {"XXBTZUSD": candles, "last": 0}}
    assert fetcher.main(["--output", str(out), "--sleep-seconds", "0"], fetch=fake) == 0
    rows = {(r["asset"], r["month"]): r["close"] for r in csv.DictReader(out.open())}
    assert rows[("bitcoin", "2013-10")] == "123.8" and rows[("bitcoin", "2026-09")] == "61000" and rows[("bitcoin", "2026-10")] == "85755"
    assert rows[("ethereum", "2026-10")] == "85755"            # every pair got the fake payload
