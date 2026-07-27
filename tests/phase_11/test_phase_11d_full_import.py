from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

def load_module():
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "run_phase_11d_full_import.py"
    spec = importlib.util.spec_from_file_location("run_phase_11d_full_import", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def test_dataset_table_contract_is_complete():
    module = load_module()
    assert set(module.DATASET_TABLES) == {
        "asset_master",
        "forecasts",
        "recommendations",
        "risk_metrics",
        "portfolio_positions",
        "platform_status",
    }

def test_status_normalization():
    module = load_module()
    assert module.normalize_status({"validation_status": "PASS"}) == "PASS"
    assert module.normalize_status({"status": "pass"}) == "PASS"
