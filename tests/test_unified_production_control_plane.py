from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pytest

from foundation.production.control_plane import (
    ControlPlaneConfig,
    PlatformConfig,
    build_command,
    run_unified_cycle,
)


def _config(tmp_path: Path) -> ControlPlaneConfig:
    uip = tmp_path / "uip"
    metals = tmp_path / "metals"
    mtg = tmp_path / "mtg"
    crypto = tmp_path / "crypto"
    for path in (uip, metals, mtg, crypto):
        path.mkdir()
    database = crypto / "crypto.duckdb"
    database.write_bytes(b"test")
    return ControlPlaneConfig(
        uip_root=uip,
        platforms={
            "metals": PlatformConfig(True, metals),
            "mtg": PlatformConfig(True, mtg),
            "crypto": PlatformConfig(True, crypto, database),
        },
    )


def test_crypto_command_sets_database_without_user_environment_workaround(tmp_path: Path) -> None:
    config = _config(tmp_path)
    command, env = build_command(config, "crypto")
    assert command[-2:] == ["--crypto-root", str(config.platforms["crypto"].repository_root)]
    assert env["CRYPTO_DATABASE_PATH"] == str(config.platforms["crypto"].database_path)


def test_all_platforms_run_in_order_and_publish_status(tmp_path: Path) -> None:
    config = _config(tmp_path)
    calls: list[list[str]] = []

    def runner(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="PASS", stderr="")

    moments = iter(
        datetime(2026, 7, 28, 18, minute, tzinfo=timezone.utc)
        for minute in range(10)
    )
    result = run_unified_cycle(
        config,
        ["metals", "mtg", "crypto"],
        runner=runner,
        now=lambda: next(moments),
    )
    assert result.status == "PASS"
    assert result.completed_platforms == ["metals", "mtg", "crypto"]
    assert len(calls) == 3
    output = config.uip_root / "data" / "operations" / "production_control_plane"
    assert (output / "latest.json").is_file()
    assert (output / "platform_status.csv").is_file()


def test_cycle_is_fail_closed_by_default(tmp_path: Path) -> None:
    config = _config(tmp_path)
    calls = 0

    def runner(command, **kwargs):
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="failed")

    result = run_unified_cycle(config, ["metals", "mtg", "crypto"], runner=runner)
    assert result.status == "FAIL"
    assert result.failed_platform == "metals"
    assert calls == 1


def test_missing_crypto_database_fails_before_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    missing = tmp_path / "missing.duckdb"
    config.platforms["crypto"] = PlatformConfig(
        True,
        config.platforms["crypto"].repository_root,
        missing,
    )
    with pytest.raises(FileNotFoundError, match="Crypto database not found"):
        run_unified_cycle(config, ["crypto"])
