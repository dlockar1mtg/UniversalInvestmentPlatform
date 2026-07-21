from __future__ import annotations

from datetime import datetime, timezone

import pytest

from foundation.production.metals_readiness import (
    _component,
    summarize_metals_readiness,
)


NOW = datetime(2026, 7, 21, 12, tzinfo=timezone.utc)


def test_readiness_summary_passes_only_when_every_component_passes() -> None:
    report = summarize_metals_readiness(
        [
            {"name": "registry", "status": "PASS", "detail": {"assets": 10}},
            {"name": "package", "status": "PASS", "detail": {"status": "READY"}},
        ],
        generated_at=NOW,
    )
    assert report["status"] == "PASS"
    assert report["ready"] is True
    assert report["failed_components"] == []


def test_readiness_summary_fails_closed_on_component_failure() -> None:
    report = summarize_metals_readiness(
        [
            {"name": "registry", "status": "PASS", "detail": {}},
            {"name": "providers", "status": "FAILED", "error_type": "ProviderError"},
        ],
        generated_at=NOW,
    )
    assert report["status"] == "FAILED"
    assert report["ready"] is False
    assert report["failed_components"] == ["providers"]


def test_readiness_summary_rejects_empty_or_naive_evaluation() -> None:
    empty = summarize_metals_readiness([], generated_at=NOW)
    assert empty["ready"] is False
    with pytest.raises(ValueError, match="timezone-aware"):
        summarize_metals_readiness([], generated_at=datetime(2026, 7, 21, 12))


def test_component_wrapper_converts_exceptions_to_failure() -> None:
    passed = _component("healthy", lambda: {"records": 9})
    failed = _component(
        "broken",
        lambda: (_ for _ in ()).throw(RuntimeError("unavailable")),
    )
    assert passed == {
        "name": "healthy",
        "status": "PASS",
        "detail": {"records": 9},
    }
    assert failed["status"] == "FAILED"
    assert failed["error_type"] == "RuntimeError"
