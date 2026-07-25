"""Fail-closed orchestration and durable evidence for the Metals production cycle."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence


_IMPORT_ID_PATTERN = re.compile(
    r"^Import ID:\s*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class MetalsCycleStage:
    name: str
    command: tuple[str, ...]
    required: bool = True


@dataclass
class MetalsStageResult:
    name: str
    status: str
    started_at_utc: str
    completed_at_utc: str
    runtime_seconds: float
    command: list[str]
    return_code: int
    stdout_tail: str = ""
    stderr_tail: str = ""


@dataclass
class MetalsCycleRecord:
    cycle_id: str
    status: str
    started_at_utc: str
    completed_at_utc: str | None
    runtime_seconds: float | None
    repository_root: str
    metals_root: str
    package_root: str
    owner: str
    notification_destination: str
    package_id: str | None = None
    import_id: str | None = None
    data_as_of_date: str | None = None
    failed_stage: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    stages: list[MetalsStageResult] = field(default_factory=list)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _tail(value: str, maximum_characters: int = 12000) -> str:
    value = value or ""
    return value[-maximum_characters:]


def extract_import_id(output: str) -> str | None:
    """Extract the final transactional import UUID from runner output."""
    matches = _IMPORT_ID_PATTERN.findall(output or "")
    return matches[-1].lower() if matches else None


def load_package_evidence(package_root: Path) -> dict[str, str | None]:
    summary_path = package_root / "package_summary.json"
    if not summary_path.exists():
        return {"package_id": None, "data_as_of_date": None}
    document = json.loads(summary_path.read_text(encoding="utf-8"))
    return {
        "package_id": document.get("package_id"),
        "data_as_of_date": (
            document.get("data_as_of_date")
            or document.get("data_as_of")
            or document.get("generated_at_utc")
        ),
    }


def persist_cycle_record(record: MetalsCycleRecord, history_root: Path) -> Path:
    history_root.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(record), indent=2, sort_keys=True) + "\n"
    record_path = history_root / f"{record.cycle_id}.json"
    record_path.write_text(payload, encoding="utf-8")
    (history_root / "latest.json").write_text(payload, encoding="utf-8")
    if record.status == "PASS":
        (history_root / "latest_success.json").write_text(payload, encoding="utf-8")
    return record_path


def default_stages(
    repository_root: Path,
    metals_root: Path,
    package_root: Path,
    *,
    skip_export: bool = False,
    skip_live_providers: bool = False,
) -> tuple[MetalsCycleStage, ...]:
    python = sys.executable
    stages: list[MetalsCycleStage] = []
    if not skip_export:
        stages.append(
            MetalsCycleStage(
                "universal_export",
                (
                    python,
                    str(repository_root / "scripts" / "run_metals_universal_export.py"),
                    "--metals-root",
                    str(metals_root),
                ),
            )
        )
    stages.append(
        MetalsCycleStage(
            "transactional_import",
            (
                python,
                str(repository_root / "scripts" / "run_metals_end_to_end.py"),
                "--metals-root",
                str(metals_root),
                "--skip-export",
            ),
        )
    )
    readiness = [
        python,
        str(repository_root / "scripts" / "check_metals_production_readiness.py"),
        "--metals-root",
        str(metals_root),
        "--package-root",
        str(package_root),
        "--output",
        str(repository_root / "data" / "operations" / "metals" / "latest_readiness.json"),
    ]
    if skip_live_providers:
        readiness.append("--skip-live-providers")
    stages.append(MetalsCycleStage("production_readiness", tuple(readiness)))
    return tuple(stages)


def run_metals_cycle(
    *,
    repository_root: Path,
    metals_root: Path,
    package_root: Path,
    history_root: Path,
    owner: str,
    notification_destination: str,
    stages: Sequence[MetalsCycleStage],
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    now: Callable[[], datetime] = utc_now,
) -> MetalsCycleRecord:
    cycle_start = now()
    record = MetalsCycleRecord(
        cycle_id=f"metals-{cycle_start.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}",
        status="RUNNING",
        started_at_utc=_iso(cycle_start),
        completed_at_utc=None,
        runtime_seconds=None,
        repository_root=str(repository_root.resolve()),
        metals_root=str(metals_root.resolve()),
        package_root=str(package_root.resolve()),
        owner=owner,
        notification_destination=notification_destination,
    )
    persist_cycle_record(record, history_root)

    for stage in stages:
        stage_start = now()
        try:
            completed = runner(
                list(stage.command),
                cwd=repository_root,
                text=True,
                capture_output=True,
                check=False,
            )
            return_code = int(completed.returncode)
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
        except Exception as exc:
            return_code = 1
            stdout = ""
            stderr = f"{type(exc).__name__}: {exc}"
        stage_end = now()
        stage_result = MetalsStageResult(
            name=stage.name,
            status="PASS" if return_code == 0 else "FAILED",
            started_at_utc=_iso(stage_start),
            completed_at_utc=_iso(stage_end),
            runtime_seconds=round((stage_end - stage_start).total_seconds(), 3),
            command=list(stage.command),
            return_code=return_code,
            stdout_tail=_tail(stdout),
            stderr_tail=_tail(stderr),
        )
        record.stages.append(stage_result)
        if stage.name == "transactional_import" and return_code == 0:
            record.import_id = extract_import_id(stdout)
            if record.import_id is None:
                record.status = "FAILED"
                record.failed_stage = stage.name
                record.errors.append(
                    "Transactional import passed but no import ID was found in its output."
                )
                persist_cycle_record(record, history_root)
                break
        persist_cycle_record(record, history_root)
        if return_code != 0 and stage.required:
            record.status = "FAILED"
            record.failed_stage = stage.name
            record.errors.append(f"Required stage failed: {stage.name}")
            break
        if return_code != 0:
            record.warnings.append(f"Optional stage failed: {stage.name}")

    if record.status == "RUNNING":
        record.status = "PASS"
    evidence = load_package_evidence(package_root)
    record.package_id = evidence["package_id"]
    record.data_as_of_date = evidence["data_as_of_date"]
    cycle_end = now()
    record.completed_at_utc = _iso(cycle_end)
    record.runtime_seconds = round((cycle_end - cycle_start).total_seconds(), 3)
    persist_cycle_record(record, history_root)
    return record
