"""Run Phase 7 live-delivery certification."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.delivery_certification import certify_phase_7

report = certify_phase_7(ROOT)
print(json.dumps(report.document(), indent=2, sort_keys=True))
raise SystemExit(0 if report.status == "PASSED" else 1)
