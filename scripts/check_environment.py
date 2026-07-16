from __future__ import annotations

import importlib
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(r"C:\Users\DevonLockard\InvestmentPlatform")
OUTPUT_FILE = ROOT / "environment" / "environment_check.txt"

PACKAGES = [
    "pandas",
    "duckdb",
    "py7zr",
    "pyppmd",
    "psutil",
]


def command_output(command: list[str]) -> str:
    """Run a command and safely return its output."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout.strip() or result.stderr.strip()

        if result.returncode != 0:
            return f"FAILED ({result.returncode}): {output}"

        return output

    except OSError as exc:
        return f"FAILED: {exc}"


def package_version(package_name: str) -> str:
    """Return an installed package version."""
    try:
        module = importlib.import_module(package_name)
        return getattr(module, "__version__", "Installed; version unavailable")
    except ImportError:
        return "NOT INSTALLED"
    except Exception as exc:
        return f"ERROR: {exc}"


def main() -> None:
    ROOT.joinpath("environment").mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "Universal Investment Intelligence Platform",
        "Development Environment Check",
        "=" * 60,
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"Operating system: {platform.platform()}",
        f"Python version: {sys.version}",
        f"Python executable: {sys.executable}",
        f"Git executable: {shutil.which('git') or 'NOT FOUND'}",
        f"VS Code executable: {shutil.which('code') or 'NOT FOUND'}",
        "",
        "Git version:",
        command_output(["git", "--version"]),
        "",
        "pip version:",
        command_output([sys.executable, "-m", "pip", "--version"]),
        "",
        "Package validation:",
    ]

    for package in PACKAGES:
        lines.append(f"- {package}: {package_version(package)}")

    lines.extend(
        [
            "",
            "Archive command validation:",
            command_output([sys.executable, "-m", "py7zr", "--version"]),
            "",
            "Workspace validation:",
        ]
    )

    required_folders = [
        "config",
        "data",
        "docs",
        "environment",
        "exchange",
        "logs",
        "registry",
        "schemas",
        "scripts",
        "tests",
    ]

    for folder_name in required_folders:
        folder = ROOT / folder_name
        status = "FOUND" if folder.exists() else "MISSING"
        lines.append(f"- {folder_name}: {status}")

    report = "\n".join(lines)
    OUTPUT_FILE.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nSaved report to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()