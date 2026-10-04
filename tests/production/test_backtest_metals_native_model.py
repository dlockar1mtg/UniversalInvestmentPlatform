import csv, importlib.util, json, math
from datetime import date
from pathlib import Path
import pytest
spec = importlib.util.spec_from_file_location("bt", Path(__file__).resolve().parents[2] / "scripts" / "backtest_metals_native_model.py")
bt = importlib.util.module_from_spec(spec)
import sys; sys.modules["bt"] = bt
spec.loader.exec_module(bt)

def monthly(n, start=(2000, 1), f=lambda i: 100 * 1.01 ** i):
    out = []
    for i in range(n):
        y, m = divmod(start[1] - 1 + i, 12)
        out.append((date(start[0] + y, m + 1, 1), f(i)))
    return out

def momentum_call(metal, points, funded):
    ret = points[-1][1] / points[-13][1] - 1
    return ("BUY" if ret > 0.05 else "HOLD"), ret

def test_model_never_sees_the_future():
    seen = []
    def spy(metal, points, funded):
        seen.append(points[-1][0]); return "HOLD", 0.0
    pts = monthly(60)
    calls = bt.walk_forward({"GOLD": pts}, spy, {"GOLD"}, date(2001, 1, 1))
    assert [c.as_of for c in calls] == seen  # each call used data ending exactly at its own date
    assert calls[0].forward_12m_return == pytest.approx(1.01 ** 12 - 1)
    assert calls[-1].forward_12m_return is None

def test_strategy_acts_with_a_one_month_lag():
    # prices jump only between months 30 and 31; a call made at month 29 earns it (t+2)
    pts = monthly(48, f=lambda i: 100.0 if i <= 30 else 110.0)
    calls = [bt.Call("GOLD", pts[i][0], "BUY" if i == 29 else "HOLD", 0.0, None) for i in range(12, 46)]
    res = bt.strategy(calls, pts, {})
    strat = res["_monthly"]["strategy"]
    assert sum(1 for r in strat if r > 0) == 1 and max(strat) == pytest.approx(0.10)
    calls_wrong = [bt.Call("GOLD", pts[i][0], "BUY" if i == 30 else "HOLD", 0.0, None) for i in range(12, 46)]
    assert max(bt.strategy(calls_wrong, pts, {})["_monthly"]["strategy"]) == 0.0  # too late, no look-ahead

def test_performance_metrics():
    p = bt.performance([0.01] * 24, [0.0] * 24)
    assert p["annual_return"] == pytest.approx(1.01 ** 12 - 1)
    assert p["max_drawdown"] == 0.0
    d = bt.performance([0.10, -0.50, 0.20], [0, 0, 0])
    assert d["max_drawdown"] == pytest.approx(-0.5)

def test_calibration_and_rank_correlation():
    calls = [bt.Call("G", date(2000, 1, i + 1), "BUY" if i % 2 else "HOLD", float(i), float(i) / 10) for i in range(10)]
    cal = bt.calibration(calls)
    assert cal["rank_correlation"] == pytest.approx(1.0)
    assert cal["by_call"]["BUY"]["months"] == 5

def test_end_to_end_with_fake_model(tmp_path):
    hist = tmp_path / "h.csv"
    with hist.open("w", newline="") as h:
        w = csv.writer(h); w.writerow(["asset_id", "observation_date", "value", "source"])
        for d, v in monthly(300, (1995, 1), lambda i: 100 * (1 + 0.3 * math.sin(i / 9))): w.writerow(["METALS:COMMODITY:GOLD", d.isoformat(), v, "wb"])
        for yr in range(1995, 2020): w.writerow(["METALS:COMMODITY:URANIUM", f"{yr}-01-01", 30 + yr % 7, "eia"])
    reg = tmp_path / "v.json"; reg.write_text(json.dumps({"vehicles": [{"ticker": "GLD", "underlying_asset_id": "metals:commodity:gold", "enabled": True, "role": "strategic"}]}))
    meth = tmp_path / "m.json"; meth.write_text(json.dumps({"models": [{"methodology_version": "2.0.0"}]}))
    out = tmp_path / "out"
    assert bt.main(["--history", str(hist), "--methodology", str(meth), "--vehicle-registry", str(reg), "--start", "2000-01-01", "--output-dir", str(out)], model_call=momentum_call) == 0
    report = json.loads((out / "backtest.json").read_text())
    assert "GOLD" in report["by_metal"] and report["calls_only"] == ["URANIUM"]
    assert report["by_metal"]["GOLD"]["model_strategy"]["months"] > 200
    assert "Equal-weight portfolio" in (out / "backtest.md").read_text()


def test_the_real_production_model_is_called_correctly():
    root = Path(__file__).resolve().parents[2]
    methodology = json.loads((root / "config" / "metals" / "model_methodology_registry.json").read_text(encoding="utf-8-sig"))
    call = bt.real_model_call(methodology)
    # Choppy prices so the production model (v3.1: value and trend) can be fitted.
    choppy = monthly(300, (2000, 1), lambda i: 100 * (1 + 0.4 * math.sin(i / 7)))
    recommendation, adjusted = call("GOLD", choppy, True)
    assert recommendation in bt.CALL_ORDER
    assert adjusted is not None and math.isfinite(adjusted)
