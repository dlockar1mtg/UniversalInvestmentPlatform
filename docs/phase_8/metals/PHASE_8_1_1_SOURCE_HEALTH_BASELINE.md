# Phase 8.1.1 — Metals Source Health Baseline

## Evaluation Date

2026-07-20

## Source Project

- Source path: C:\Users\DevonLockard\metals
- Source repository status: Not a Git repository
- Python version: 3.14.6
- Current Metals generation: v8
- Source audit size: 267 files

## Metals Test Baseline

The original test suite stopped during collection because
tests/test_database.py imports retired module-level connect and migrate
functions and queries SQLite metadata.

The current implementation uses:

- Database class
- Database.connect()
- Database.initialize()
- DuckDB

The database test is classified as a stale pre-DuckDB test.

After excluding only that obsolete test:

    python -m pytest .\tests -q --ignore=.\tests\test_database.py

Result:

    22 passed in 2.00s

## Universal Platform Regression Baseline

The Universal Investment Intelligence Platform test suite was also run before
Metals integration changes.

Result:

    1026 passed, 1 warning in 7.36s

The warning is a non-blocking Starlette deprecation warning involving the
FastAPI test client.

## Assessment

Both systems have healthy pre-integration baselines. The Metals application
will not be merged wholesale. Components will be classified as:

1. Adopt
2. Adapt
3. Replace with universal capability
4. Archive

Only valuable Metals-specific capabilities not already supplied by the
universal platform will be integrated.
