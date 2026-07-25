from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from foundation.production.metals_cycle import (
    MetalsCycleStage,
    persist_cycle_record,
    run_metals_cycle,
)


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 25, 14, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        current = self.value
        self.value += timedelta(seconds=1)
        return current


def _package(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "package_summary.json").write_text(
        json.dumps(
            {
                "package_id": "metals-test-package",
                "generated_at_utc": "2026-07-25T13:59:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    return root


def test_cycle_persists_success_and_latest_success(tmp_path: Path) -> None:
    package_root = _package(tmp_path / "package")
    history_root = tmp_path / "history"

    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="PASS", stderr="")

    record = run_metals_cycle(
        repository_root=tmp_path,
        metals_root=tmp_path / "metals",
        package_root=package_root,
        history_root=history_root,
        owner="test-owner",
        notification_destination="test-console",
        stages=(
            MetalsCycleStage("export", ("python", "export.py")),
            MetalsCycleStage("readiness", ("python", "readiness.py")),
        ),
        runner=runner,
        now=Clock(),
    )

    assert record.status == "PASS"
    assert record.package_id == "metals-test-package"
    assert [stage.status for stage in record.stages] == ["PASS", "PASS"]
    assert (history_root / "latest.json").exists()
    assert (history_root / "latest_success.json").exists()


def test_required_failure_stops_later_stages(tmp_path: Path) -> None:
    package_root = _package(tmp_path / "package")
    history_root = tmp_path / "history"
    calls: list[str] = []

    def runner(command, **kwargs):
        calls.append(command[-1])
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="boom")

    record = run_metals_cycle(
        repository_root=tmp_path,
        metals_root=tmp_path / "metals",
        package_root=package_root,
        history_root=history_root,
        owner="test-owner",
        notification_destination="test-console",
        stages=(
            MetalsCycleStage("failed", ("python", "failed.py")),
            MetalsCycleStage("must_not_run", ("python", "later.py")),
        ),
        runner=runner,
        now=Clock(),
    )

    assert record.status == "FAILED"
    assert record.failed_stage == "failed"
    assert calls == ["failed.py"]
    assert len(record.stages) == 1
    assert not (history_root / "latest_success.json").exists()


def test_persist_cycle_record_replaces_latest_atomically_enough_for_local_use(tmp_path: Path) -> None:
    package_root = _package(tmp_path / "package")

    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    record = run_metals_cycle(
        repository_root=tmp_path,
        metals_root=tmp_path / "metals",
        package_root=package_root,
        history_root=tmp_path / "history",
        owner="owner",
        notification_destination="console",
        stages=(MetalsCycleStage("one", ("python", "one.py")),),
        runner=runner,
        now=Clock(),
    )
    path = persist_cycle_record(record, tmp_path / "history")
    assert path.exists()
    latest = json.loads((tmp_path / "history" / "latest.json").read_text(encoding="utf-8"))
    assert latest["cycle_id"] == record.cycle_id
