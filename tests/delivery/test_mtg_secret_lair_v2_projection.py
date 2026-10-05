import csv, json
from datetime import date
from pathlib import Path
import pytest
from foundation.presentation.mtg_secret_lair_v2_projection import build_secret_lair_v2_records, REQUIRED_COLUMNS, RECORD_TYPE

def write(path, fields, rows):
    with path.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields); w.writeheader(); w.writerows(rows)

def decision(product, call, gap="0.12", net="0.05", rank="1"):
    row = {c: "" for c in REQUIRED_COLUMNS}
    row.update(secret_lair_id=product, product_name=f"Drop {product}", as_of="2026-10-04", market_price="50", buy_price="44",
               buy_price_basis="LOWEST_LISTING", gap=gap, expected_return_6m="0.2", expected_net_return_6m=net, call=call, rank=rank,
               ranked_products="2", model_version="secret-lair-v2")
    return row

def files(tmp, rows):
    d = tmp / "secret_lair_v2_decisions.csv"; write(d, list(REQUIRED_COLUMNS), rows)
    d.with_suffix(".json").write_text(json.dumps({"as_of": "2026-10-04", "buy_gap": 0.10, "sell_cost": 0.13, "horizon_months": 6,
                                                   "calibration": {"intercept": 0.15, "slope": 0.52, "pairs": 11190}}))
    e = tmp / "export.csv"
    write(e, ["mtg_asset_id", "mtg_lane", "native_asset_id", "product_name"], [
        {"mtg_asset_id": "SECRET_LAIR_V1_1|SL-A", "mtg_lane": "SECRET_LAIR_V1_1", "native_asset_id": "SL-A", "product_name": "A"},
        {"mtg_asset_id": "SECRET_LAIR_V1_1|SL-B", "mtg_lane": "SECRET_LAIR_V1_1", "native_asset_id": "SL-B", "product_name": "B"},
        {"mtg_asset_id": "SECRET_LAIR_V1_1|SL-GONE", "mtg_lane": "SECRET_LAIR_V1_1", "native_asset_id": "SL-GONE", "product_name": "Gone"},
        {"mtg_asset_id": "COLLECTOR_V1|X", "mtg_lane": "COLLECTOR_V1", "native_asset_id": "X", "product_name": "Box"}])
    return d, e

def test_one_record_per_secret_lair_asset(tmp_path):
    d, e = files(tmp_path, [decision("SL-A", "BUY"), decision("SL-B", "WAIT", gap="0.02", net="-0.01", rank="2"), decision("SL-NOT-IN-UIP", "WAIT", gap="0", net="-0.02")])
    recs = build_secret_lair_v2_records(d, e, today=date(2026, 10, 5))
    assert [r.asset_id for r in recs] == ["SECRET_LAIR_V1_1|SL-A", "SECRET_LAIR_V1_1|SL-B", "SECRET_LAIR_V1_1|SL-GONE"]
    assert all(r.record_type == RECORD_TYPE and r.domain_id == "mtg" and r.record_key == r.asset_id for r in recs)
    a, b, gone = (r.payload for r in recs)
    assert a["call"] == "BUY" and a["buy_price"] == "44" and a["research_model"] == "secret-lair-v2" and a["price_age_days"] == 1
    assert a["calibration_slope"] == 0.52 and a["sell_cost"] == 0.13
    assert b["call"] == "WAIT"
    assert gone["call"] == "NO_PRICE" and gone["note"] == "NOT_IN_DAILY_PRICE_FEED" and gone["product_name"] == "Gone"

@pytest.mark.parametrize("bad, message", [
    (decision("SL-A", "SELL"), "Unknown"),
    (decision("SL-A", "BUY", gap="0.05"), "does not meet"),
    (decision("SL-A", "BUY", net="-0.01"), "does not meet"),
])
def test_invalid_decisions_are_refused(tmp_path, bad, message):
    d, e = files(tmp_path, [bad])
    with pytest.raises(RuntimeError, match=message):
        build_secret_lair_v2_records(d, e)

def test_missing_summary_is_refused(tmp_path):
    d, e = files(tmp_path, [decision("SL-A", "BUY")])
    d.with_suffix(".json").unlink()
    with pytest.raises(RuntimeError, match="summary"):
        build_secret_lair_v2_records(d, e)


def test_publication_uses_v2_only_when_enabled(tmp_path, monkeypatch):
    from foundation.presentation import publication_model
    d, e = files(tmp_path, [decision("SL-A", "BUY")])
    monkeypatch.setenv("UIP_MTG_SECRET_LAIR_V2_PATH", str(d))
    monkeypatch.setenv("UIP_MTG_EXPORT_PAYLOAD_PATH", str(e))
    monkeypatch.delenv("UIP_MTG_PREMIUM_SIDECAR_PATH", raising=False)
    monkeypatch.delenv("UIP_MTG_SECRET_LAIR_V2_ENABLED", raising=False)
    assert publication_model._mtg_premium_records_from_environment() == []      # off: August path (unset here)
    monkeypatch.setenv("UIP_MTG_SECRET_LAIR_V2_ENABLED", "1")
    records = publication_model._mtg_premium_records_from_environment()
    assert len(records) == 3 and records[0].payload["research_model"] == "secret-lair-v2"


def test_price_history_and_tcgplayer_id_reach_the_record(tmp_path):
    d, e = files(tmp_path, [decision("SL-A", "BUY")])
    d.with_name("secret_lair_v2_history.json").write_text(json.dumps({"SL-A": [["2026-09", 50, 44], ["2026-10", 50, 44]]}))
    recs = build_secret_lair_v2_records(d, e)
    a, gone = recs[0].payload, recs[2].payload
    assert a["price_history"] == [["2026-09", 50, 44], ["2026-10", 50, 44]] and gone["price_history"] == []
    assert a["tcgplayer_product_id"] == ""
    # outcome ranges are optional columns: absent in the decisions file, present but empty in the record
    assert all(k in a and a[k] is None for k in ("range_low_6m", "range_high_6m", "prob_profit_6m", "similar_cases"))
