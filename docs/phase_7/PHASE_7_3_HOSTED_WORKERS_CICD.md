# Phase 7.3 — Hosted Workers, Scheduling, and CI/CD

Phase 7.3 adds horizontally safe PostgreSQL job claims, a local SQLite backend, retry and lease recovery, recurring schedule buckets, graceful worker shutdown, container services, and GitHub Actions CI.

## Runtime processes

- API: `python scripts/run_production_api.py`
- Worker: `python scripts/run_production_worker.py`
- Scheduler: `python scripts/run_production_scheduler.py`

Production uses `UIIP_JOB_DATABASE_BACKEND=postgresql` and `UIIP_DATABASE_URL`. Local development may use `UIIP_JOB_DATABASE_BACKEND=sqlite` and `UIIP_JOB_SQLITE_PATH`. Worker timing is configured with `UIIP_WORKER_POLL_SECONDS`, `UIIP_WORKER_LEASE_SECONDS`, and `UIIP_WORKER_MAX_ATTEMPTS`.

Schedules are supplied as JSON through `UIIP_SCHEDULES_JSON`. Each item contains `schedule_id`, `job_type`, `interval_seconds`, and optional `payload`. Supported built-in jobs are `portfolio_validate` and `provider_check`. API keys remain environment-only.

The workflow at `.github/workflows/ci.yml` runs the complete test suite and bytecode compilation on pushes and pull requests. `.github/workflows/container.yml` builds the image for pull requests and publishes commit-addressed and `latest` images to GitHub Container Registry only from `main`, using the repository-scoped `GITHUB_TOKEN`.
