"""Preview a holdings CSV without importing it."""

import json
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "foundation" / "production" / "portfolio.py"
SPEC = importlib.util.spec_from_file_location("uiip_portfolio_validation", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load portfolio validation module")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
preview_portfolio_csv = MODULE.preview_portfolio_csv

if len(sys.argv) != 2:
    raise SystemExit("Usage: python scripts/validate_portfolio_csv.py PATH_TO_CSV")

report = preview_portfolio_csv(Path(sys.argv[1]))
print(json.dumps({
    "valid": report.valid,
    "accepted_rows": len(report.positions),
    "errors": [error.__dict__ for error in report.errors],
    "fingerprint": report.fingerprint,
}, indent=2, sort_keys=True))
raise SystemExit(0 if report.valid else 1)
