"""Write this publication run's outcome to PostgreSQL so failures reach the dashboard.

Runs as the last step of the production publication workflow, whether or not the
earlier steps succeeded.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.publication_outcomes import (  # noqa: E402
    normalize_outcome,
    record_outcome,
    summarize_reason,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-status", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--error-log", type=Path)
    args = parser.parse_args(argv)

    dsn = os.environ.get("UIIP_DATABASE_URL", "")
    if not dsn.strip():
        print("UIIP_DATABASE_URL is missing; publication outcome not recorded", file=sys.stderr)
        return 1

    outcome = normalize_outcome(args.job_status)
    reason = None
    if outcome != "SUCCESS" and args.error_log is not None and args.error_log.exists():
        reason = summarize_reason(
            args.error_log.read_text(encoding="utf-8", errors="replace"),
            redact=(dsn, os.environ.get("SOURCE_TOKEN", "")),
        )

    import psycopg

    record_outcome(
        lambda: psycopg.connect(dsn),
        run_id=args.run_id,
        workflow=args.workflow,
        outcome=outcome,
        reason=reason,
        run_url=args.run_url,
    )
    print(f"PUBLICATION_OUTCOME run={args.run_id} outcome={outcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
