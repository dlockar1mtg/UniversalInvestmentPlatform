"""Run the Phase 5.4 Universal Decision Orchestration certification."""

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from foundation.intelligence.orchestration.certification import certify_phase_5_4


report = certify_phase_5_4()
print(report.to_json())
raise SystemExit(0 if report.passed else 1)
