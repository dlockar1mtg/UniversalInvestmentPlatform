import csv
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("cv2proj", ROOT / "scripts" / "build_crypto_v2_projections.py")
pj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pj)


def _months(n, start=(2014, 1)):
    return [f"{start[0] + (start[1] - 1 + i) // 12:04d}-{(start[1] - 1 + i) % 12 + 1:02d}" for i in range(n)]


def _closes(tmp_path, n=150, seed=3):
    rng = np.random.default_rng(seed)
    path = tmp_path / "closes.csv"
    with path.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=["asset", "month", "close", "source", "updated_utc"])
        w.writeheader()
        for asset in ("bitcoin", "ethereum"):
            price = 100.0
            for m in _months(n):
                price *= float(np.exp(rng.normal(0.02, 0.15)))
                w.writerow({"asset": asset, "month": m, "close": f"{price:.6f}", "source": "TEST", "updated_utc": "2026-10-05T00:15:00Z"})
    return path


def test_simulation_is_reproducible_and_sorted():
    v = np.random.default_rng(1).normal(0.01, 0.1, 72)
    a, b = pj.simulate(v, 12, 500, 42), pj.simulate(v, 12, 500, 42)
    assert np.array_equal(a, b) and np.all(np.diff(a) >= 0)


def test_projection_structure_and_consistency(tmp_path):
    closes, _ = pj.load(_closes(tmp_path))
    pr = pj.project("bitcoin", closes["bitcoin"])
    assert pr["status"] in {"VALIDATED", "PROVISIONAL", "NOT_VALIDATED"}
    for k, h in pr["horizons"].items():
        q = h["prices"]
        assert q["p10"] <= q["p25"] <= q["p50"] <= q["p75"] <= q["p90"]
        assert (h["prob_up"] > 0.5) == (q["p50"] > pr["price"]) or abs(q["p50"] / pr["price"] - 1) < 0.02   # probabilities agree with the middle
        assert h["kind"] == ("SCENARIO" if k == "36" else pr["status"])
    assert ("36" in pr["horizons"]) == (pr["status"] == "VALIDATED")
    v = pr["validation_12m"]["raw"]
    assert v["tests"] <= pj.RECENT_TESTS and set(v) >= {"above_median", "inside_50", "inside_80", "passes"}


def test_short_history_is_not_validated(tmp_path):
    closes, _ = pj.load(_closes(tmp_path, n=60))
    assert pj.project("ethereum", closes["ethereum"])["status"] == "NOT_VALIDATED"


def test_log_appends_once_per_day_and_scores_due_entries(tmp_path):
    log = tmp_path / "log.csv"
    proj = {"bitcoin": {"price": 100.0, "price_month": "2025-10", "method": "MONTE_CARLO",
                        "horizons": {"12": {"kind": "VALIDATED", "prices": {"p10": 60, "p25": 80, "p50": 100, "p75": 130, "p90": 170}, "prob_up": 0.5}}}}
    closes = {"bitcoin": [("2025-10", 100.0), ("2026-10", 120.0)]}
    assert pj.update_log(log, proj, closes, "2025-10-05") == 1
    assert pj.update_log(log, proj, closes, "2025-10-05") == 1          # same day: no duplicate
    row = list(csv.DictReader(log.open()))[0]
    assert row["due_month"] == "2026-10" and row["outcome_price"] == "120" and row["outcome_percentile"] == "p50-p75"
    assert row["inside_50"] == "True" and row["inside_80"] == "True"


def test_runs_as_a_script(tmp_path):
    out, log = tmp_path / "proj.json", tmp_path / "log.csv"
    assert pj.main(["--closes", str(_closes(tmp_path)), "--output", str(out), "--log", str(log)]) == 0
    j = json.loads(out.read_text())
    assert j["as_of"] == "2026-10-05" and set(j["projections"]) == {"bitcoin", "ethereum"} and log.is_file()
