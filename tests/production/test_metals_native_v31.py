import json
import math
from datetime import date
from pathlib import Path

from foundation.production.metals_native_cycle import NativeObservation, _v3_predictions, evaluate_native_cycle

ROOT = Path(__file__).resolve().parents[2]


def _monthly(n, f, start=(1975, 1)):
    out = []
    for i in range(n):
        y, m = divmod(start[1] - 1 + i, 12)
        out.append((date(start[0] + y, m + 1, 15), f(i)))
    return out


def _metals():
    series = {f"METALS:COMMODITY:M{k}": _monthly(600, lambda i, k=k: 100 * math.exp(0.5 * math.sin((i + 40 * k) / 40))) for k in range(8)}
    series["METALS:COMMODITY:URANIUM"] = [(date(y, 1, 1), 30.0 + y % 5) for y in range(1975, 2026)]
    return series


def test_v3_ranks_metals_and_calls_the_top_three_buy():
    predictions = _v3_predictions(_metals())
    assert len(predictions) == 8 and "METALS:COMMODITY:URANIUM" not in predictions
    ordered = sorted(predictions.values(), key=lambda p: p["rank"])
    assert [p["rank"] for p in ordered] == list(range(1, 9))
    assert [p["recommendation"] for p in ordered] == ["BUY"] * 3 + ["HOLD"] * 5
    assert all(a["expected_return_12m"] >= b["expected_return_12m"] for a, b in zip(ordered, ordered[1:]))
    assert ordered[0]["coefficients"]["value"] < 0          # cheaper than its 10-year average -> higher expected


def test_v3_needs_enough_monthly_history():
    assert _v3_predictions({"X": _monthly(50, lambda i: 100.0)}) == {}


def test_production_cycle_uses_v3_calls_and_records_them():
    methodology = json.loads((ROOT / "config" / "metals" / "model_methodology_registry.json").read_text(encoding="utf-8-sig"))
    rows = [NativeObservation(asset, day.isoformat(), value, "test") for asset, points in _metals().items() for day, value in points]
    report = evaluate_native_cycle(rows, [], methodology)
    twelve = {f.asset_id.upper(): f for f in report.forecasts if int(f.horizon_months) == 12}
    monthly = {k: f for k, f in twelve.items() if not k.endswith("URANIUM")}
    assert sum(f.recommendation == "BUY" for f in monthly.values()) == 3
    components = {k: json.loads(f.component_json) for k, f in monthly.items()}
    assert sorted(c["v3"]["rank"] for c in components.values()) == list(range(1, 9))
    assert all(c["model_version"] == "metals-native-v3.1" for c in components.values())
    # The 12-month range is v3.1's own error band around its expected return.
    for k, c in components.items():
        assert c["range_basis"] == "V3_1_MODEL_ERRORS_P10_P90"
        assert c["bear_value"] < monthly[k].projected_value < c["bull_value"]
    uranium = twelve["METALS:COMMODITY:URANIUM"]
    assert uranium.recommendation == "HOLD"
    assert any(r.startswith("V3_NOT_MODELED_NON_MONTHLY_HISTORY") for r in report.reason_codes)


def test_a_metal_whose_latest_price_is_late_does_not_get_compared_on_a_different_month():
    series = _metals()
    late = "METALS:COMMODITY:M3"
    series[late] = series[late][:-1]                         # its newest month is missing
    predictions = _v3_predictions(series)
    assert {p["as_of_month"] for p in predictions.values()} == {"2024-11"}   # everyone scored at the late metal's month
    assert late in predictions
    far = _metals()
    far[late] = far[late][:-5]                               # five months behind: left unranked, the others go on
    p2 = _v3_predictions(far)
    assert late not in p2 and {p["as_of_month"] for p in p2.values()} == {"2024-12"} and len(p2) == 7
