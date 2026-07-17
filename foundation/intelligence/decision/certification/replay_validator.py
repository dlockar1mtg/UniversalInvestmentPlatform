"""Serialized decision replay certification."""
from datetime import datetime, timezone
from time import perf_counter
from typing import Callable
from .certification_result import CertificationResult

def validate_replay(original: object, replay: Callable[[], object]) -> CertificationResult:
    started = perf_counter(); reconstructed = replay()
    fields = ("decision_id", "asset_id", "action", "status", "eligibility", "confidence",
              "maximum_allocation", "recommended_allocation", "generated_at", "expires_at")
    mismatches = [name for name in fields if getattr(original, name) != getattr(reconstructed, name)]
    return CertificationResult("replay", not mismatches, perf_counter() - started,
        datetime.now(timezone.utc), {"fields_checked": len(fields), "mismatches": mismatches},
        "Decision replay preserved all certified fields." if not mismatches else "Replay mismatch detected.")
