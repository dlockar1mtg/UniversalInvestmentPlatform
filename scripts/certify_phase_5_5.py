"""Run Phase 5.5 certification from a source checkout."""

from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.intelligence.monitoring.certification import certify_phase_5_5


report = certify_phase_5_5()
print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
raise SystemExit(0 if report.status == "PASSED" else 1)
