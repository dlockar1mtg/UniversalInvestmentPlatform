from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SOURCE_ROOTS = [
    Path(r"C:\Users\DevonLockard\mtg-investment-terminal"),
    Path(r"C:\Users\DevonLockard\mtg-source"),
    Path(r"C:\Users\DevonLockard\mtg_investment"),
]

OUTPUT_ROOT = Path(
    r"C:\Users\DevonLockard\InvestmentPlatform-MTG-Reconciliation"
    r"\docs\project_control\generated\mtg_orchestration_inventory"
)

IGNORED_DIRECTORIES = {
    ".git",
    ".github",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "archive",
    "archives",
    "backup",
    "backups",
}

ENTRYPOINT_NAME_PATTERNS = (
    "run",
    "pipeline",
    "orchestrat",
    "workflow",
    "daily",
    "nightly",
    "refresh",
    "update",
    "export",
    "build",
    "generate",
    "schedule",
    "production",
    "main",
)

SIDE_EFFECT_PATTERNS = {
    "database_write": re.compile(
        r"\b(INSERT|UPDATE|DELETE|CREATE\s+TABLE|DROP\s+TABLE|MERGE\s+INTO)\b",
        re.IGNORECASE,
    ),
    "subprocess": re.compile(
        r"\b(subprocess|os\.system|Popen|check_call|check_output)\b",
        re.IGNORECASE,
    ),
    "network": re.compile(
        r"\b(requests\.|httpx\.|urllib\.|aiohttp\.|yfinance|api[_-]?key)\b",
        re.IGNORECASE,
    ),
    "file_write": re.compile(
        r"\b(to_csv|to_json|to_excel|write_text|write_bytes|open\([^)]*[\"']w)",
        re.IGNORECASE,
    ),
    "scheduler": re.compile(
        r"\b(schedule|cron|apscheduler|task scheduler|nightly|daily job)\b",
        re.IGNORECASE,
    ),
    "duckdb": re.compile(r"\bduckdb\b", re.IGNORECASE),
    "sqlite": re.compile(r"\bsqlite3?\b", re.IGNORECASE),
}


@dataclass
class InventoryRow:
    source_root: str
    relative_path: str
    suffix: str
    size_bytes: int
    sha256: str
    likely_entrypoint: bool
    has_main_guard: bool
    python_functions: str
    python_classes: str
    imports: str
    detected_side_effects: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def is_ignored(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(part.lower() in IGNORED_DIRECTORIES for part in relative_parts)


def iter_candidate_files(root: Path) -> Iterable[Path]:
    extensions = {
        ".py",
        ".ps1",
        ".bat",
        ".cmd",
        ".sh",
        ".sql",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
    }

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if is_ignored(path, root):
            continue

        if path.suffix.lower() not in extensions:
            continue

        yield path


def parse_python(path: Path) -> tuple[list[str], list[str], list[str], bool]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], [], [], '__name__ == "__main__"' in text

    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            functions.append(node.name)

        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)

        elif isinstance(node, ast.Import):
            imports.extend(
                alias.name
                for alias in node.names
            )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)

    has_main_guard = (
        '__name__ == "__main__"' in text
        or "__name__ == '__main__'" in text
    )

    return (
        sorted(set(functions)),
        sorted(set(classes)),
        sorted(set(imports)),
        has_main_guard,
    )


def inspect_file(root: Path, path: Path) -> InventoryRow:
    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        text = ""

    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []
    has_main_guard = False

    if path.suffix.lower() == ".py":
        (
            functions,
            classes,
            imports,
            has_main_guard,
        ) = parse_python(path)

    filename_lower = path.name.lower()

    likely_entrypoint = (
        has_main_guard
        or any(
            token in filename_lower
            for token in ENTRYPOINT_NAME_PATTERNS
        )
    )

    side_effects = [
        name
        for name, pattern in SIDE_EFFECT_PATTERNS.items()
        if pattern.search(text)
    ]

    return InventoryRow(
        source_root=str(root),
        relative_path=path.relative_to(root).as_posix(),
        suffix=path.suffix.lower(),
        size_bytes=path.stat().st_size,
        sha256=sha256(path),
        likely_entrypoint=likely_entrypoint,
        has_main_guard=has_main_guard,
        python_functions=" | ".join(functions),
        python_classes=" | ".join(classes),
        imports=" | ".join(imports),
        detected_side_effects=" | ".join(side_effects),
    )


def write_csv(
    path: Path,
    rows: list[InventoryRow],
) -> None:
    fieldnames = list(
        InventoryRow.__dataclass_fields__.keys()
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(asdict(row))


def main() -> int:
    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_rows: list[InventoryRow] = []
    source_summary: list[dict[str, object]] = []

    for root in SOURCE_ROOTS:
        if not root.exists():
            source_summary.append(
                {
                    "source_root": str(root),
                    "exists": False,
                    "candidate_files": 0,
                    "likely_entrypoints": 0,
                }
            )
            continue

        rows = [
            inspect_file(root, path)
            for path in iter_candidate_files(root)
        ]

        rows.sort(
            key=lambda row: (
                not row.likely_entrypoint,
                row.relative_path.lower(),
            )
        )

        all_rows.extend(rows)

        source_summary.append(
            {
                "source_root": str(root),
                "exists": True,
                "candidate_files": len(rows),
                "likely_entrypoints": sum(
                    row.likely_entrypoint
                    for row in rows
                ),
                "main_guard_files": sum(
                    row.has_main_guard
                    for row in rows
                ),
            }
        )

    all_rows.sort(
        key=lambda row: (
            row.source_root.lower(),
            not row.likely_entrypoint,
            row.relative_path.lower(),
        )
    )

    write_csv(
        OUTPUT_ROOT / "mtg_orchestration_file_inventory.csv",
        all_rows,
    )

    entrypoints = [
        row
        for row in all_rows
        if row.likely_entrypoint
    ]

    write_csv(
        OUTPUT_ROOT / "mtg_orchestration_entrypoints.csv",
        entrypoints,
    )

    summary = {
        "generated_at_utc": (
            datetime.now(timezone.utc).isoformat()
        ),
        "execution_mode": "READ_ONLY_STATIC_INSPECTION",
        "source_summary": source_summary,
        "total_candidate_files": len(all_rows),
        "total_likely_entrypoints": len(entrypoints),
        "side_effect_counts": {
            name: sum(
                name in row.detected_side_effects.split(" | ")
                for row in all_rows
            )
            for name in SIDE_EFFECT_PATTERNS
        },
    }

    (
        OUTPUT_ROOT
        / "mtg_orchestration_inventory_summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("MTG ORCHESTRATION INVENTORY: COMPLETE")
    print(
        f"Candidate files: {len(all_rows)}"
    )
    print(
        f"Likely entrypoints: {len(entrypoints)}"
    )

    for source in source_summary:
        print(
            f"- {source['source_root']}: "
            f"exists={source['exists']}, "
            f"files={source['candidate_files']}, "
            f"entrypoints={source['likely_entrypoints']}"
        )

    print(
        "Inventory:",
        OUTPUT_ROOT
        / "mtg_orchestration_file_inventory.csv",
    )
    print(
        "Entrypoints:",
        OUTPUT_ROOT
        / "mtg_orchestration_entrypoints.csv",
    )
    print(
        "Summary:",
        OUTPUT_ROOT
        / "mtg_orchestration_inventory_summary.json",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
