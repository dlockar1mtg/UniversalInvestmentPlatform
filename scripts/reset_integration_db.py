from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "integration" / "uiip_integration.duckdb"

RELATED_FILES = [
    DATABASE_PATH,
    Path(str(DATABASE_PATH) + ".wal"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset the generated UIIP integration database."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required confirmation flag",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.confirm:
        print(
            "No files were deleted. Run with --confirm to reset "
            "the generated integration database."
        )
        return 2

    deleted = 0

    for path in RELATED_FILES:
        if path.exists():
            path.unlink()
            print(f"Deleted: {path}")
            deleted += 1

    if deleted == 0:
        print("Integration database was already absent.")
    else:
        print(f"Deleted {deleted} generated database file(s).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())