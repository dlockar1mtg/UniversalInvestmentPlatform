"""The Watchtower must not keep a 'credentials required' error from before the key was entered (Nov 23, 2026)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "foundation/production/dashboard_assets/watchtower.js"
HARNESS = ROOT / "tests/js/watchtower_key_harness.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_watchtower_waits_for_the_key_then_reads():
    out = subprocess.run(["node", str(HARNESS), str(SCRIPT)], capture_output=True, text=True, timeout=30, check=True).stdout
    before, after = out.strip().splitlines()
    assert "Enter your dashboard key" in before and "fetches 0" in before
    assert "credentials" not in after and "fetches 1" in after


def test_watchtower_script_is_ascii():
    SCRIPT.read_text(encoding="ascii")
