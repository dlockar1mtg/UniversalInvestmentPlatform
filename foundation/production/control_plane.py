"""Unified fail-closed production control plane for UIP source platforms."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
import csv
import json
import os
import subprocess
import sys
import uuid


SUPPORTED_PLATFORMS = ("metals", "mtg", "crypto")


@dataclass(frozen=True)
class PlatformConfig:
    enabled: bool
    repository_root: Path
    database_path: Path | None = None
    skip_live_providers: bool = False


@dataclass(frozen=True)
class ControlPlaneConfig:
    uip_root: Path
    platforms: dict[str, PlatformConfig]


@dataclass
class PlatformCycleResult:
    platform: str
    status: str
    started_at_utc: str
    completed_at_utc: str
    runtime_seconds: float
    command: list[str]
    return_code: int
    stdout_tail: str = ""
    stderr_tail: str = ""


@dataclass
class UnifiedCycleResult:
    cycle_id: str
    status: str
    started_at_utc: str
    completed_at_utc: str
    requested_platforms: list[str]
    completed_platforms: list[str] = field(default_factory=list)
    failed_platform: str | None = None
    platform_results: list[PlatformCycleResult] = field(default_factory=list)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _tail(value: str, maximum: int = 12000) -> str:
    return (value or "")[-maximum:]


def load_control_plane_config(path: Path) -> ControlPlaneConfig:
    payload = json.loads(path.resolve().read_text(encoding="utf-8"))
    uip_root = Path(payload["uip_root"]).expanduser().resolve()
    platforms: dict[str, PlatformConfig] = {}
    for name in SUPPORTED_PLATFORMS:
        row = payload.get("platforms", {}).get(name, {})
        root_value = row.get("repository_root")
        if not root_value:
            raise ValueError(f"Missing repository_root for {name}")
        database = row.get("database_path")
        platforms[name] = PlatformConfig(
            enabled=bool(row.get("enabled", True)),
            repository_root=Path(root_value).expanduser().resolve(),
            database_path=Path(database).expanduser().resolve() if database else None,
            skip_live_providers=bool(row.get("skip_live_providers", False)),
        )
    return ControlPlaneConfig(uip_root=uip_root, platforms=platforms)


def validate_config(config: ControlPlaneConfig, selected: Iterable[str]) -> None:
    if not config.uip_root.is_dir():
        raise FileNotFoundError(f"UIP repository not found: {config.uip_root}")
    for name in selected:
        if name not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {name}")
        platform = config.platforms[name]
        if not platform.enabled:
            raise ValueError(f"Platform is disabled: {name}")
        if not platform.repository_root.is_dir():
            raise FileNotFoundError(
                f"{name} repository not found: {platform.repository_root}"
            )
        if name == "crypto":
            if platform.database_path is None:
                raise ValueError("Crypto database_path is required")
            if not platform.database_path.is_file():
                raise FileNotFoundError(
                    f"Crypto database not found: {platform.database_path}"
                )


def build_command(config: ControlPlaneConfig, platform: str) -> tuple[list[str], dict[str, str]]:
    python = sys.executable
    root = config.uip_root
    source = config.platforms[platform]
    env = os.environ.copy()
    if platform == "metals":
        command = [
            python,
            str(root / "scripts" / "run_metals_production_cycle.py"),
            "--metals-root",
            str(source.repository_root),
        ]
        if source.skip_live_providers:
            command.append("--skip-live-providers")
        return command, env
    if platform == "mtg":
        return [
            python,
            str(root / "scripts" / "run_mtg_manual_production_cycle.py"),
            "--mtg-root",
            str(source.repository_root),
        ], env
    env["CRYPTO_DATABASE_PATH"] = str(source.database_path)
    return [
        python,
        str(root / "scripts" / "run_crypto_manual_production_cycle.py"),
        "--crypto-root",
        str(source.repository_root),
    ], env


def write_unified_status(result: UnifiedCycleResult, output_root: Path) -> tuple[Path, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    payload = asdict(result)
    json_path = output_root / "latest.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    history = output_root / "history"
    history.mkdir(parents=True, exist_ok=True)
    (history / f"{result.cycle_id}.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    csv_path = output_root / "platform_status.csv"
    fields = [
        "cycle_id", "platform", "status", "started_at_utc", "completed_at_utc",
        "runtime_seconds", "return_code",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in result.platform_results:
            writer.writerow({"cycle_id": result.cycle_id, **{key: getattr(item, key) for key in fields[1:]}})
    return json_path, csv_path


def run_unified_cycle(
    config: ControlPlaneConfig,
    selected: Iterable[str],
    *,
    continue_on_failure: bool = False,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    now: Callable[[], datetime] = _utc_now,
) -> UnifiedCycleResult:
    platforms = list(dict.fromkeys(selected))
    validate_config(config, platforms)
    started = now()
    result = UnifiedCycleResult(
        cycle_id=f"uip-production-{started.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}",
        status="RUNNING",
        started_at_utc=_iso(started),
        completed_at_utc="",
        requested_platforms=platforms,
    )
    output_root = config.uip_root / "data" / "operations" / "production_control_plane"
    write_unified_status(result, output_root)

    for platform in platforms:
        command, env = build_command(config, platform)
        stage_start = now()
        completed = runner(
            command,
            cwd=config.uip_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        stage_end = now()
        item = PlatformCycleResult(
            platform=platform,
            status="PASS" if completed.returncode == 0 else "FAIL",
            started_at_utc=_iso(stage_start),
            completed_at_utc=_iso(stage_end),
            runtime_seconds=round((stage_end - stage_start).total_seconds(), 3),
            command=command,
            return_code=int(completed.returncode),
            stdout_tail=_tail(completed.stdout or ""),
            stderr_tail=_tail(completed.stderr or ""),
        )
        result.platform_results.append(item)
        if item.status == "PASS":
            result.completed_platforms.append(platform)
        else:
            result.failed_platform = platform
            result.status = "FAIL"
        write_unified_status(result, output_root)
        if item.status == "FAIL" and not continue_on_failure:
            break

    if result.status == "RUNNING":
        result.status = "PASS"
    result.completed_at_utc = _iso(now())
    write_unified_status(result, output_root)
    return result
