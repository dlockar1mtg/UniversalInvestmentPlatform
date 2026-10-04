import csv, importlib.util, json, math, subprocess, sys
from datetime import date
from pathlib import Path
import pytest
SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
spec = importlib.util.spec_from_file_location("v32", SCRIPTS / "research_metals_v32.py")
v32 = importlib.util.module_from_spec(spec); sys.modules["v32"] = v32; spec.loader.exec_module(v32)

def monthly(n, f, start=(1970, 1)):
    out = []
    for i in range(n):
        y, m = divmod(start[1] - 1 + i, 12)
        out.append((date(start[0] + y, m + 1, 1), f(i)))
    return out

def series():
    return {f"M{k}": monthly(640, lambda i, k=k: 100 * math.exp(0.5 * math.sin((i + 30 * k) / 37) + 0.2 * math.cos(i / 11 + k))) for k in range(5)}

def test_ols_recovers_three_coefficients():
    xs = [[math.sin(i), math.cos(i * 1.3), math.sin(i * 0.7) * 2] for i in range(300)]
    y = [0.02 + 0.5 * a - 0.3 * b + 0.1 * c for a, b, c in xs]
    assert v32.ols(xs, y) == pytest.approx([0.02, 0.5, -0.3, 0.1], abs=1e-9)

def test_walk_forward_uses_only_known_outcomes():
    s = series()
    seen = []
    real = v32.ols
    def spy(x, y):
        seen.append(len(y)); return real(x, y)
    v32.ols = spy
    try:
        bands = v32.walk_forward(s, "v3.2c both", date(1980, 1, 1), date(2006, 1, 1), date(2009, 12, 1))
    finally:
        v32.ols = real
    assert seen == sorted(seen) and len(seen) == 4          # one refit per year, training grows
    rows = v32.rows_for(s)
    for year, n in zip(range(2006, 2010), seen):
        expected = sum(1 for r in rows if r["date"] >= date(1980, 1, 1) and r["forward"] is not None and s[r["metal"]][r["i"] + 12][0] < date(year, 1, 1))
        assert n == expected
    assert all(low <= e <= high for e, low, high in bands.values())

def test_capping_limits_extreme_features():
    s = series()
    s["M0"] = [(d, v * (50 if i > 600 else 1)) for i, (d, v) in enumerate(s["M0"])]   # extreme late spike
    capped = v32.walk_forward(s, "v3.2a capped", date(1980, 1, 1), date(2021, 1, 1), date(2022, 12, 1))
    raw = v32.walk_forward(s, "v3.1", date(1980, 1, 1), date(2021, 1, 1), date(2022, 12, 1))
    spike = [k for k in raw if k[0] == "M0" and k[1] > 600]
    assert spike and max(abs(capped[k][0]) for k in spike) < max(abs(raw[k][0]) for k in spike)

def test_runs_as_a_script(tmp_path):
    hist = tmp_path / "h.csv"
    with hist.open("w", newline="") as h:
        w = csv.writer(h); w.writerow(["asset_id", "observation_date", "value", "source"])
        for m, pts in series().items():
            for d, v in pts:
                w.writerow([f"METALS:COMMODITY:{m}", d.isoformat(), v, "wb"])
    out = tmp_path / "o"
    proc = subprocess.run([sys.executable, str(SCRIPTS / "research_metals_v32.py"), "--history", str(hist), "--output-dir", str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    rep = json.loads((out / "v32_research.json").read_text())
    assert set(rep["results"]) == set(v32.VARIANTS)
    assert all(0.5 <= r["range_coverage"] <= 1.0 for r in rep["results"].values())
    assert "Adoption rule" in (out / "v32_research.md").read_text()
