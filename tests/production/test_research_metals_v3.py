import csv, importlib.util, json, math, sys
from datetime import date
from pathlib import Path
import pytest
SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
spec = importlib.util.spec_from_file_location("v3", SCRIPTS / "research_metals_v3.py")
v3 = importlib.util.module_from_spec(spec); sys.modules["v3"] = v3; spec.loader.exec_module(v3)

def monthly(n, f, start=(1970, 1)):
    out = []
    for i in range(n):
        y, m = divmod(start[1] - 1 + i, 12)
        out.append((date(start[0] + y, m + 1, 1), f(i)))
    return out

def test_calls_follow_the_dashboard_thresholds():
    assert [v3.call_for(x) for x in (0.2, 0.06, 0.0, -0.08, -0.3)] == ["STRONG_BUY", "BUY", "HOLD", "REDUCE", "AVOID"]

def test_features_use_only_past_data():
    pts = monthly(200, lambda i: 100 * 1.01 ** i)
    assert v3.features(pts, 118) is None
    value, trend = v3.features(pts, 150)
    later = [(d, v * (10 if k > 150 else 1)) for k, (d, v) in enumerate(pts)]
    assert v3.features(later, 150) == pytest.approx((value, trend))   # future prices change nothing

def test_fit_recovers_a_known_relationship():
    rows = []
    for k in range(400):
        val, tr = math.sin(k) * 0.5, math.cos(k * 1.7) * 0.2
        rows.append(("X", k, date(1990, 1, 1), val, tr, 0.03 - 0.2 * val + 0.5 * tr))
    a, b, c = v3.fit(rows)
    assert (a, b, c) == pytest.approx((0.03, -0.2, 0.5), abs=1e-9)

def test_end_to_end_on_mean_reverting_prices(tmp_path):
    hist = tmp_path / "h.csv"
    with hist.open("w", newline="") as h:
        w = csv.writer(h); w.writerow(["asset_id", "observation_date", "value", "source"])
        for metal, k in (("GOLD", 37), ("COPPER", 53)):
            for d, v in monthly(670, lambda i: 100 * math.exp(0.5 * math.sin(i / k))):
                w.writerow([f"METALS:COMMODITY:{metal}", d.isoformat(), v, "wb"])
    out = tmp_path / "o"
    assert v3.main(["--history", str(hist), "--output-dir", str(out)]) == 0
    rep = json.loads((out / "v3_research.json").read_text())
    assert rep["coefficients"]["value"] < 0                          # cheap -> higher expected return
    assert rep["out_of_sample"]["rank_correlation"] > 0.3
    assert "Out-of-sample" in (out / "v3_research.md").read_text()

def test_walk_forward_only_uses_outcomes_known_before_each_year():
    def price(i): return 100 * math.exp(0.4 * math.sin(i / 23)) * 1.002 ** i
    series = {"GOLD": monthly(500, price), "COPPER": monthly(500, lambda i: price(i + 7))}
    seen = []
    real_fit = v3.fit
    def spy(rows):
        seen.append(max(series[r[0]][r[1] + 12][0] for r in rows)); return real_fit(rows)
    v3.fit = spy
    try:
        preds, yearly = v3.walk_forward_predictions(series, date(1980, 1, 1), date(2006, 1, 1), date(2010, 12, 1))
    finally:
        v3.fit = real_fit
    assert sorted(yearly) == [2006, 2007, 2008, 2009, 2010]
    assert all(latest < date(year, 1, 1) for latest, year in zip(seen, sorted(yearly)))
    assert all(series[m][i][0].year in yearly for (m, i) in preds)

def test_top_k_holds_the_highest_expected_metals():
    series = {m: monthly(200, lambda i, k=k: 100 * (1 + 0.01 * k) ** i) for k, m in enumerate(["A", "B", "C", "D"])}
    preds = {(m, i): float(k) for k, m in enumerate(["A", "B", "C", "D"]) for i in range(150, 190)}
    perf = v3.rule_strategies(series, preds, {}, top_k=2)
    assert perf["top_k"]["annual_return"] > perf["hold"]["annual_return"]   # C and D grow fastest and are picked
