"""Record and read the outcome of every production publication run, including failures.

The active publication only describes the last run that succeeded, so a failed run
is otherwise invisible to the dashboard. Each publication run writes one row here,
whatever its result, and the refresh status reads the most recent row.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from typing import Callable, Iterable

TABLE = "publication_run_outcomes"

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    run_id TEXT PRIMARY KEY,
    workflow TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('SUCCESS', 'FAILURE', 'CANCELLED')),
    reason TEXT,
    run_url TEXT,
    recorded_at_utc TIMESTAMPTZ NOT NULL
)
"""

UPSERT_SQL = f"""
INSERT INTO {TABLE} (run_id, workflow, outcome, reason, run_url, recorded_at_utc)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (run_id) DO UPDATE SET
    outcome = EXCLUDED.outcome,
    reason = EXCLUDED.reason,
    run_url = EXCLUDED.run_url,
    recorded_at_utc = EXCLUDED.recorded_at_utc
"""

LATEST_SQL = f"""
SELECT run_id, workflow, outcome, reason, run_url, recorded_at_utc
FROM {TABLE}
ORDER BY recorded_at_utc DESC
LIMIT 1
"""

_OUTCOMES = {"success": "SUCCESS", "failure": "FAILURE", "cancelled": "CANCELLED"}
_COLUMNS = ("run_id", "workflow", "outcome", "reason", "run_url", "recorded_at_utc")


def normalize_outcome(job_status: str) -> str:
    """Map a GitHub Actions job.status value to a stored outcome."""
    try:
        return _OUTCOMES[job_status.strip().lower()]
    except KeyError:
        raise ValueError(f"unknown job status: {job_status!r}") from None


def summarize_reason(
    log_text: str,
    *,
    redact: Iterable[str] = (),
    max_lines: int = 3,
    max_chars: int = 500,
) -> str | None:
    """Keep the last few non-empty error lines, with any secret values removed."""
    for value in redact:
        if value:
            log_text = log_text.replace(value, "[redacted]")
    lines = [line.strip() for line in log_text.splitlines() if line.strip()]
    if not lines:
        return None
    return " | ".join(lines[-max_lines:])[:max_chars]


def record_outcome(
    connection_factory: Callable[[], object],
    *,
    run_id: str,
    workflow: str,
    outcome: str,
    reason: str | None,
    run_url: str | None,
    now: datetime | None = None,
) -> None:
    if outcome not in _OUTCOMES.values():
        raise ValueError(f"unknown outcome: {outcome!r}")
    recorded_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    with closing(connection_factory()) as db:
        with db.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
            cursor.execute(UPSERT_SQL, (run_id, workflow, outcome, reason, run_url, recorded_at))
        db.commit()


def latest_outcome(connection_factory: Callable[[], object]) -> dict[str, object] | None:
    """Return the most recent recorded run, or None if nothing has been recorded yet."""
    with closing(connection_factory()) as db, db.cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s)", (TABLE,))
        exists = cursor.fetchone()
        if exists is None or exists[0] is None:
            return None
        cursor.execute(LATEST_SQL)
        row = cursor.fetchone()
    if row is None:
        return None
    item = dict(zip(_COLUMNS, row))
    recorded_at = item["recorded_at_utc"]
    if isinstance(recorded_at, datetime):
        item["recorded_at_utc"] = recorded_at.astimezone(timezone.utc).isoformat()
    return item
