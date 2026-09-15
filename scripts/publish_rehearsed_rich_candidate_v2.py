"""Publish the exact rehearsed rich candidate with governed Metals implementation records.

This wrapper preserves the certified production publisher and injects only the already-
rehearsed Metals vehicle implementation projection. It exists so the production path
matches the 14,238-record read-only candidate without rewriting the prior bounded
publisher. No ranking is recalculated here.
"""
from __future__ import annotations

from pathlib import Path

import scripts.publish_rehearsed_rich_candidate as publisher
from foundation.presentation.metals_rich_projection import build_metals_rich_records as build_core_metals_rich_records
from foundation.presentation.metals_vehicle_implementation_projection import (
    RECORD_TYPE as METALS_IMPLEMENTATION_RECORD_TYPE,
    build_metals_vehicle_implementation_records,
)
from scripts.rehearse_rich_publication_candidate import expected_metals_counts as expected_core_metals_counts

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IMPLEMENTATION_RECORD_COUNT = 10


def build_metals_rich_records_with_implementation(artifact_root: Path):
    """Return the exact certified Metals rich rows plus the governed implementation rows."""
    core = list(build_core_metals_rich_records(artifact_root))
    implementations = list(build_metals_vehicle_implementation_records(ROOT))
    if len(implementations) != EXPECTED_IMPLEMENTATION_RECORD_COUNT:
        raise RuntimeError(
            "Metals implementation production projection count drifted: "
            f"expected={EXPECTED_IMPLEMENTATION_RECORD_COUNT} observed={len(implementations)}"
        )
    if any(record.record_type != METALS_IMPLEMENTATION_RECORD_TYPE for record in implementations):
        raise RuntimeError("Unexpected record type in Metals implementation production projection")
    return core + implementations


def expected_metals_counts_with_implementation(artifact_root: Path) -> dict[str, int]:
    expected = dict(expected_core_metals_counts(artifact_root))
    if METALS_IMPLEMENTATION_RECORD_TYPE in expected:
        raise RuntimeError("Metals implementation record type unexpectedly collides with core rich family")
    expected[METALS_IMPLEMENTATION_RECORD_TYPE] = EXPECTED_IMPLEMENTATION_RECORD_COUNT
    return expected


def main() -> int:
    # Patch only the two bounded extension points consumed by the certified publisher.
    # The legacy publisher still owns source pinning, preactivation validation,
    # PostgreSQL sequencing, atomic activation, and evidence emission.
    publisher.build_metals_rich_records = build_metals_rich_records_with_implementation
    publisher.expected_metals_counts = expected_metals_counts_with_implementation
    return publisher.main()


if __name__ == "__main__":
    raise SystemExit(main())
