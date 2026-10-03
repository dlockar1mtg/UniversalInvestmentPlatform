import csv, importlib.util, json, math, sys
from datetime import date
from pathlib import Path
import pytest
SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
spec = importlib.util.spec_from_file_location("sr", SCRIPTS / "research_metals_signals.py")
sr = importlib.util.module_from_spec(spec); sys.modules["sr"] = sr; spec.loader.exec_module(sr)

def monthly(n, start=(1975, 1), f=lambda i: 100.0):
    out = []
    for i in range(n):
        y, m = divmod(start[1] - 1 + i, 12)
        out.append((date(start[0] + y, m + 1, 1), f(i)))
    return out

def test_rules():
    up = monthly(130, f=lambda i: 100 * 1.01 ** i)
    assert sr.moving_average(10)(up)[0] is True
    assert sr.mean_reversion(12)(up)[0] is False
    assert sr.value(10)(up)[0] is False          # price above its 10-year average
    assert sr.value(10)(up[:100]) is None        # not enough history
    down = monthly(130, f=lambda i: 100 * 0.99 ** i)
    assert sr.mean_reversion(12)(down)[0] is True and sr.moving_average(10)(down)[0] is False

def test_switch_costs_and_no_lookahead():
    pts = monthly(80, f=lambda i: 100 * (1.02 if (i // 6) % 2 else 0.98) ** (i % 6))
    seen = []
    def spy(points):
        seen.append(points[-1][0]); return (len(points) % 2 == 0, 0.0)
    res = sr.evaluate({"GOLD": pts}, lambda metal: spy, {}, date(1976, 1, 1), date(1990, 1, 1))
    assert seen == sorted(seen) and all(d >= date(1976, 1, 1) for d in seen)
    assert res["per_metal"]["GOLD"]["switches"] > 10    # alternating positions are charged each time

def test_settings_chosen_in_sample_only(tmp_path):
    # in-sample: trending (moving average wins); out-of-sample: oscillating
    def price(i):
        return 100 * 1.01 ** i if i < 372 else 100 * 1.01 ** 372 * (1 + 0.25 * math.sin((i - 372) / 3))
    series = {"GOLD": monthly(600, (1975, 1), price), "SILVER": monthly(600, (1975, 1), lambda i: price(i) * 1.1)}
    rep = sr.research(series, None, set(), {}, (date(1980, 1, 1), date(2005, 12, 31)), (date(2006, 1, 1), date(2025, 1, 1)))
    assert set(rep["families"]) == {"mean_reversion", "moving_average", "value"}
    ma = rep["families"]["moving_average"]
    assert ma["chosen_setting"] in ma["in_sample_by_setting"] and ma["out_of_sample"]["metals"] == 2

def test_main_end_to_end(tmp_path):
    hist = tmp_path / "h.csv"
    with hist.open("w", newline="") as h:
        w = csv.writer(h); w.writerow(["asset_id", "observation_date", "value", "source"])
        for metal, k in (("GOLD", 9), ("COPPER", 7)):
            for d, v in monthly(600, (1975, 1), lambda i: 100 * (1 + 0.3 * math.sin(i / k)) * 1.003 ** i):
                w.writerow([f"METALS:COMMODITY:{metal}", d.isoformat(), v, "wb"])
    reg = tmp_path / "v.json"; reg.write_text(json.dumps({"vehicles": []}))
    out = tmp_path / "o"
    fake = lambda metal, points, funded: ("BUY" if points[-1][1] > points[-13][1] else "HOLD", 0.0)
    assert sr.main(["--history", str(hist), "--vehicle-registry", str(reg), "--output-dir", str(out)], model_call=fake) == 0
    rep = json.loads((out / "signal_research.json").read_text())
    assert set(rep["families"]) == {"mean_reversion", "moving_average", "value", "current_model"}
    assert "Out-of-sample" in (out / "signal_research.md").read_text()
