from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from foundation.production.free_staging_certification import certify_phase_7_6
report = certify_phase_7_6(ROOT)
print(json.dumps(report.document(), indent=2, sort_keys=True))
raise SystemExit(0 if report.status == "PASSED" else 1)
