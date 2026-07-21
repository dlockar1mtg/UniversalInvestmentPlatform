from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from exchange.metals.adapter import adapter as adapter_module
from exchange.metals.adapter.config import load_config
from exchange.metals.adapter.contracts import Contract, ContractField

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


@pytest.mark.parametrize(
    ("freshness_status", "expected_status", "expected_warnings"),
    [("PASS", "SUCCESS", 0), ("STALE", "PARTIAL", 1)],
)
def test_platform_status_maps_native_freshness_to_canonical_contract(
    tmp_path: Path,
    freshness_status: str,
    expected_status: str,
    expected_warnings: int,
) -> None:
    exports = tmp_path / "exports"
    exports.mkdir()
    pd.DataFrame([
        {"decision_run_id": 9, "explanation": "health evidence"}
    ]).to_csv(exports / "latest_platform_health_score.csv", index=False)
    pd.DataFrame([
        {
            "series_key": "gold",
            "last_observation": "2026-07-20",
            "age_days": 1,
            "freshness_status": freshness_status,
        }
    ]).to_csv(exports / "latest_data_freshness_details.csv", index=False)
    context = adapter_module.BuildContext(
        Path.cwd(),
        tmp_path,
        tmp_path / "output",
        tmp_path / "schemas",
        load_config(Path("exchange/metals/config/adapter_config.json")),
        "package-1",
        "2026-07-21T12:00:00+00:00",
    )
    contract = Contract(
        "platform_status",
        (
            ContractField("run_id", True),
            ContractField("run_started_at_utc", True),
            ContractField("run_completed_at_utc", False),
            ContractField("run_status", True),
            ContractField("data_as_of_date", True),
            ContractField("warning_count", True),
            ContractField("error_count", True),
        ),
    )
    row = adapter_module._platform_status(context, contract, exports).iloc[0]
    assert str(row["run_id"]) == "9"
    assert row["run_status"] == expected_status
    assert row["data_as_of_date"] == "2026-07-20"
    assert row["warning_count"] == expected_warnings
    assert row["error_count"] == 0
