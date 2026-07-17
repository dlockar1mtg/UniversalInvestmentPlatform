"""Deterministic-output certification."""
from datetime import datetime, timezone
from time import perf_counter
from typing import Callable
from .certification_result import CertificationResult

def validate_determinism(factory: Callable[[], str], repetitions: int = 3) -> CertificationResult:
    started = perf_counter()
    outputs = [factory() for _ in range(repetitions)]
    passed = len(set(outputs)) == 1
    return CertificationResult("determinism", passed, perf_counter() - started,
        datetime.now(timezone.utc), {"repetitions": repetitions},
        "Serialized decisions are deterministic." if passed else "Serialized decisions differed.")
