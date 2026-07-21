from __future__ import annotations

import json
from pathlib import Path

from foundation.production.metals_final import (
    REQUIRED_CERTIFICATIONS,
    scan_runtime_isolation,
)


def test_live_runtime_has_no_legacy_import_or_database_coupling() -> None:
    result = scan_runtime_isolation(Path.cwd())
    assert result["status"] == "PASS"
    assert result["violations"] == []
    assert result["legacy_database_fallback_default"] is False


def test_runtime_isolation_detects_legacy_import(tmp_path: Path) -> None:
    foundation = tmp_path / "foundation"
    adapter = tmp_path / "exchange" / "metals" / "adapter"
    foundation.mkdir()
    adapter.mkdir(parents=True)
    (foundation / "bad.py").write_text(
        "from metals_platform.database import Database\n",
        encoding="utf-8",
    )
    (adapter / "adapter.py").write_text("", encoding="utf-8")
    result = scan_runtime_isolation(tmp_path)
    assert result["status"] == "FAILED"
    assert result["violations"][0]["path"] == "foundation/bad.py"


def test_adapter_release_version_is_consistent() -> None:
    version = Path("exchange/metals/adapter/VERSION").read_text(encoding="utf-8").strip()
    config = json.loads(
        Path("exchange/metals/config/adapter_config.json").read_text(encoding="utf-8")
    )
    assert version == "2.0.0"
    assert config["adapter_version"] == version


def test_final_gate_requires_every_prior_phase_certificate() -> None:
    assert len(REQUIRED_CERTIFICATIONS) == 9
    root = Path("docs/phase_8/metals")
    assert all((root / name).is_file() for name in REQUIRED_CERTIFICATIONS)
    assert (root / "METALS_LEGACY_RETIREMENT_RUNBOOK.md").is_file()
