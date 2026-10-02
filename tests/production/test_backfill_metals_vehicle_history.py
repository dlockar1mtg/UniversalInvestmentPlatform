import csv
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "backfill_metals_vehicle_history.py"


def _module():
    spec = importlib.util.spec_from_file_location("backfill_metals_vehicle_history", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _registry(tmp_path):
    path = tmp_path / "vehicles.json"
    path.write_text(json.dumps({"vehicles": [
        {"ticker": "GLDM", "enabled": True, "role": "strategic"},
        {"ticker": "OLD", "enabled": False, "role": "strategic"},
    ]}))
    return path


def _frame(days, start="2023-10-02"):
    index = pd.bdate_range(start=start, periods=days)
    return pd.DataFrame(
        {"Close": [80.0 + i * 0.01 for i in range(days)], "Adj Close": [80.0 + i * 0.01 for i in range(days)],
         "Volume": [2_500_000 + i for i in range(days)]},
        index=index,
    )


def test_backfill_writes_rows_the_ingest_step_can_read(tmp_path):
    module = _module()
    output = tmp_path / "out.csv"
    code = module.main(["--tickers", "gldm", "--output", str(output), "--registry", str(_registry(tmp_path))],
                       fetch=lambda ticker, period: _frame(750))
    assert code == 0
    with output.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 750
    assert rows[0]["ticker"] == "GLDM" and rows[0]["trading_date"] == "2023-10-02"
    # Columns the existing load_vehicle_csv reads: ticker, trading_date, close_price, adjusted_close, volume, source.
    assert set(rows[0]) == {"ticker", "trading_date", "close_price", "adjusted_close", "volume", "source"}
    assert float(rows[0]["volume"]) == 2_500_000.0


def test_backfill_refuses_unregistered_or_disabled_tickers(tmp_path):
    module = _module()
    with pytest.raises(SystemExit, match="not enabled"):
        module.main(["--tickers", "OLD", "--output", str(tmp_path / "o.csv"), "--registry", str(_registry(tmp_path))],
                    fetch=lambda ticker, period: _frame(750))


def test_backfill_refuses_too_little_history(tmp_path):
    module = _module()
    with pytest.raises(SystemExit, match="only 100 daily rows"):
        module.main(["--tickers", "GLDM", "--output", str(tmp_path / "o.csv"), "--registry", str(_registry(tmp_path))],
                    fetch=lambda ticker, period: _frame(100))
