"""Final Phase 3.2 framework certification checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FrameworkCertificationResult:
    """Final structural certification result for Phase 3.2."""

    passed: bool
    required_files_checked: int
    missing_files: tuple[str, ...]
    message: str


REQUIRED_PHASE_3_2_FILES = (
    "foundation/intelligence/validation/historical_observation.py",
    "foundation/intelligence/validation/prediction_record.py",
    "foundation/intelligence/validation/outcome_record.py",
    "foundation/intelligence/validation/walk_forward_engine.py",
    "foundation/intelligence/validation/validation_metrics_engine.py",
    "foundation/intelligence/validation/benchmark_comparison_engine.py",
    "foundation/intelligence/validation/cross_asset_engine.py",
    "foundation/intelligence/validation/validation_reporting.py",
    "foundation/intelligence/validation/report_serialization.py",
    "foundation/intelligence/validation/dashboard_dataset.py",
    "config/intelligence/validation/validation_profiles.yaml",
    "config/intelligence/validation/benchmark_definitions.yaml",
)


def certify_phase_3_2_structure(
    root: str | Path,
) -> FrameworkCertificationResult:
    repository_root = Path(root)
    missing = tuple(
        path
        for path in REQUIRED_PHASE_3_2_FILES
        if not (repository_root / path).exists()
    )
    passed = not missing
    return FrameworkCertificationResult(
        passed=passed,
        required_files_checked=len(REQUIRED_PHASE_3_2_FILES),
        missing_files=missing,
        message=(
            "Phase 3.2 structural certification passed."
            if passed
            else "Phase 3.2 structural certification failed."
        ),
    )
