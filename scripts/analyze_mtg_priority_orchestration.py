from __future__ import annotations

import ast
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path(
    r"C:\Users\DevonLockard\mtg-investment-terminal"
)

SECONDARY_ROOT = Path(
    r"C:\Users\DevonLockard\mtg-source"
)

INVENTORY_ROOT = Path(
    r"C:\Users\DevonLockard\InvestmentPlatform-MTG-Reconciliation"
    r"\docs\project_control\generated\mtg_orchestration_inventory"
)

CANDIDATE_FILE = (
    INVENTORY_ROOT
    / "mtg_canonical_orchestration_candidates.csv"
)


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    return ""


def literal_value(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def read_priority_candidates() -> list[dict[str, str]]:
    with CANDIDATE_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if row["priority_candidate"].lower() == "true"
        ]


def inspect_file(
    source_root: Path,
    relative_path: str,
) -> dict[str, Any]:
    path = source_root / relative_path

    if not path.exists():
        return {
            "source_root": str(source_root),
            "relative_path": relative_path,
            "exists": False,
        }

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        return {
            "source_root": str(source_root),
            "relative_path": relative_path,
            "exists": True,
            "parse_status": "SYNTAX_ERROR",
            "parse_error": str(error),
        }

    imports: set[str] = set()
    functions: list[dict[str, Any]] = []
    classes: list[str] = []
    operational_calls: list[dict[str, Any]] = []
    argparse_arguments: list[dict[str, Any]] = []
    subprocess_commands: list[dict[str, Any]] = []
    path_literals: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")

        elif isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            functions.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "arguments": [
                        argument.arg
                        for argument in node.args.args
                    ],
                }
            )

        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)

        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                value = node.value

                if (
                    "\\" in value
                    or "/" in value
                    or value.endswith(
                        (
                            ".csv",
                            ".json",
                            ".db",
                            ".duckdb",
                            ".sqlite",
                            ".yaml",
                            ".yml",
                        )
                    )
                ):
                    path_literals.add(value)

        elif isinstance(node, ast.Call):
            call_name = dotted_name(node.func)

            if call_name.endswith("add_argument"):
                argparse_arguments.append(
                    {
                        "line": node.lineno,
                        "arguments": [
                            literal_value(argument)
                            for argument in node.args
                        ],
                        "keywords": {
                            keyword.arg: literal_value(
                                keyword.value
                            )
                            for keyword in node.keywords
                            if keyword.arg is not None
                        },
                    }
                )

            operational_markers = (
                "subprocess.run",
                "subprocess.Popen",
                "subprocess.check_call",
                "subprocess.check_output",
                "os.system",
                "runpy.run_path",
                "duckdb.connect",
                "sqlite3.connect",
                "Path.write_text",
                "Path.write_bytes",
                "to_csv",
                "to_json",
                "to_excel",
                "shutil.copy",
                "shutil.copy2",
                "shutil.copytree",
            )

            if any(
                marker in call_name
                for marker in operational_markers
            ):
                call_record = {
                    "line": node.lineno,
                    "call": call_name,
                    "arguments": [
                        literal_value(argument)
                        for argument in node.args
                    ],
                    "keywords": {
                        keyword.arg: literal_value(
                            keyword.value
                        )
                        for keyword in node.keywords
                        if keyword.arg is not None
                    },
                }

                operational_calls.append(call_record)

                if "subprocess" in call_name:
                    subprocess_commands.append(
                        call_record
                    )

    return {
        "source_root": str(source_root),
        "relative_path": relative_path,
        "exists": True,
        "parse_status": "PASS",
        "imports": sorted(imports),
        "functions": sorted(
            functions,
            key=lambda item: item["line"],
        ),
        "classes": sorted(classes),
        "argparse_arguments": argparse_arguments,
        "operational_calls": operational_calls,
        "subprocess_commands": subprocess_commands,
        "path_literals": sorted(path_literals),
        "line_count": len(text.splitlines()),
    }


def main() -> int:
    candidates = read_priority_candidates()

    canonical_results = [
        inspect_file(
            SOURCE_ROOT,
            row["relative_path"],
        )
        for row in candidates
    ]

    conflict_paths = [
        row["relative_path"]
        for row in candidates
        if row["secondary_copy_status"]
        == "different_in_secondary"
    ]

    conflict_results = [
        {
            "relative_path": relative_path,
            "canonical": inspect_file(
                SOURCE_ROOT,
                relative_path,
            ),
            "secondary": inspect_file(
                SECONDARY_ROOT,
                relative_path,
            ),
        }
        for relative_path in conflict_paths
    ]

    output = {
        "generated_at_utc": (
            datetime.now(timezone.utc).isoformat()
        ),
        "execution_mode": "READ_ONLY_STATIC_ANALYSIS",
        "priority_candidate_count": len(candidates),
        "canonical_results": canonical_results,
        "conflict_results": conflict_results,
    }

    output_path = (
        INVENTORY_ROOT
        / "mtg_priority_orchestration_static_analysis.json"
    )

    output_path.write_text(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("MTG PRIORITY ORCHESTRATION ANALYSIS: COMPLETE")
    print("Priority candidates:", len(candidates))
    print("Conflicting source files:", len(conflict_paths))
    print("Output:", output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
