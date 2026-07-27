from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "run_uip_quick_output.py"
    spec = importlib.util.spec_from_file_location("run_uip_quick_output", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_required_contract_contains_standard_files():
    module = load_module()
    assert "portfolio_positions.csv" in module.REQUIRED
    assert "package_summary.json" in module.REQUIRED


def test_summary_status_normalizes_values():
    module = load_module()
    assert module.summary_status({"status": "pass"}) == "PASS"
