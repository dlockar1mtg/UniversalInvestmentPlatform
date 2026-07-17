"""Run Phase 5.1 Decision Engine certification."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from foundation.intelligence.decision.certification import (
    DecisionCertificationRunner,
)


def main() -> int:
    report = DecisionCertificationRunner().run(
        repository_root=ROOT
    )

    destination = (
        ROOT
        / "docs"
        / "phase_5"
        / "PHASE_5_1_CERTIFICATION_REPORT.md"
    )

    destination.write_text(
        report.to_markdown(),
        encoding="utf-8",
    )

    print(report.to_markdown())
    print(f"Report: {destination}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
