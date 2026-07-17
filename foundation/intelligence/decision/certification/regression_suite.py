"""Reusable scenario-regression certification."""
from datetime import datetime, timezone
from time import perf_counter
from typing import Callable, Iterable
from .certification_result import CertificationResult

def validate_scenarios(scenarios: Iterable[tuple[str, Callable[[], bool]]]) -> CertificationResult:
    started = perf_counter(); failures = []; count = 0
    for name, predicate in scenarios:
        count += 1
        try:
            if not predicate(): failures.append(name)
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    return CertificationResult("regression", not failures, perf_counter() - started,
        datetime.now(timezone.utc), {"scenario_count": count, "failures": failures},
        "All regression scenarios passed." if not failures else "Regression failures detected.")
