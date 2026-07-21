from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

EXCLUDED_DIRECTORIES = {
    ".git", ".pytest_cache", "__pycache__", ".venv", "venv",
    "data", "exports", "logs",
}
EXCLUDED_SUFFIXES = {
    ".csv", ".db", ".duckdb", ".parquet", ".pyc", ".pyo",
    ".sqlite", ".sqlite3", ".zip",
}
BACKUP_MARKERS = ("_before_", ".bak", ".backup")
VERSION_PATTERN = re.compile(r"(?:^|[_-])v(\d+(?:[_\.-]\d+)*)", re.IGNORECASE)


@dataclass(frozen=True)
class InventoryRecord:
    relative_path: str
    component: str
    role: str
    suffix: str
    size_bytes: int
    sha256: str
    version_marker: str
    is_test: bool
    is_backup: bool
    initial_classification: str
    classification_reason: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _component(relative: Path) -> str:
    parts = relative.parts
    if len(parts) >= 2 and parts[0] == "crypto_platform":
        return parts[1] if len(parts) > 2 else "root"
    if parts[0] in {"config", "docs", "sql", "tests"}:
        return parts[0]
    return "root"


def _role(relative: Path) -> str:
    name = relative.name.lower()
    if relative.parts[0] == "tests" or name.startswith(("test_", "smoke_test")):
        return "test"
    if name.startswith(
        ("run_", "apply_", "install_", "repair_", "recover_", "restore_",
         "migrate_", "upgrade_", "scan_", "diagnose_")
    ):
        return "operations"
    if name.startswith(("export_", "inspect_", "verify_", "import_")):
        return "integration"
    if relative.suffix.lower() == ".sql":
        return "schema"
    if relative.suffix.lower() in {".md", ".txt"}:
        return "documentation"
    if relative.parts[0] == "config":
        return "configuration"
    return "source"


def _classification(relative: Path, role: str, backup: bool) -> tuple[str, str]:
    component = _component(relative)
    if backup:
        return "archive", "Historical backup or pre-upgrade source"
    if role == "operations":
        return "archive", "Legacy upgrade, recovery, or operational entry point"
    if component in {"ml", "optimization"}:
        return "replace", "Universal platform already owns generic ML and optimization"
    if role == "test":
        return "evaluate", "Script may preserve Crypto-specific expected behavior"
    if role == "configuration":
        return "adapt", "Potentially reusable Crypto asset, provider, or policy configuration"
    if role in {"integration", "schema"}:
        return "evaluate", "Required to determine the canonical v13 integration boundary"
    if role == "documentation":
        return "reference_only", "Historical capability and release evidence"
    return "evaluate", "Requires component-level domain review"


def iter_source_files(source_root: Path) -> Iterable[Path]:
    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source_root)
        if any(part in EXCLUDED_DIRECTORIES for part in relative.parts[:-1]):
            continue
        if path.name.lower().startswith(".env"):
            continue
        if path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        yield path


def build_inventory(source_root: Path) -> list[InventoryRecord]:
    records: list[InventoryRecord] = []
    for path in iter_source_files(source_root):
        relative = path.relative_to(source_root)
        relative_text = relative.as_posix()
        backup = any(marker in relative_text.lower() for marker in BACKUP_MARKERS)
        role = _role(relative)
        classification, reason = _classification(relative, role, backup)
        match = VERSION_PATTERN.search(relative.stem)
        records.append(
            InventoryRecord(
                relative_path=relative_text,
                component=_component(relative),
                role=role,
                suffix=path.suffix.lower(),
                size_bytes=path.stat().st_size,
                sha256=_sha256(path),
                version_marker=match.group(1).replace("_", ".") if match else "",
                is_test=role == "test",
                is_backup=backup,
                initial_classification=classification,
                classification_reason=reason,
            )
        )
    return records


def write_inventory(records: list[InventoryRecord], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [asdict(record) for record in records]
    stem = "crypto_component_inventory"
    with (output_dir / f"{stem}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(InventoryRecord.__dataclass_fields__)
        )
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / f"{stem}.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    summary = {
        "file_count": len(records),
        "total_size_bytes": sum(record.size_bytes for record in records),
        "components": dict(sorted(Counter(r.component for r in records).items())),
        "roles": dict(sorted(Counter(r.role for r in records).items())),
        "initial_classifications": dict(
            sorted(Counter(r.initial_classification for r in records).items())
        ),
        "backup_file_count": sum(record.is_backup for record in records),
        "test_file_count": sum(record.is_test for record in records),
    }
    (output_dir / f"{stem}_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory an external Crypto source tree.")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_root = args.source_root.resolve()
    if not (source_root / "crypto_platform").is_dir():
        raise SystemExit(f"Not a Crypto source root: {source_root}")
    records = build_inventory(source_root)
    write_inventory(records, args.output_dir.resolve())
    print(f"Inventoried {len(records)} files.")
    print(f"Output: {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
