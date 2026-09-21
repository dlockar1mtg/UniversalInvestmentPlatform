"""Compatibility entry point for the governed rich production publisher."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.publish_rehearsed_rich_candidate as publisher


def main() -> int:
    return publisher.main()


if __name__ == "__main__":
    raise SystemExit(main())
