# Phase 7.1 — HTTP Service and Production Database

Phase 7.1 exposes the certified production API through FastAPI and adds a PostgreSQL implementation of the durable run, artifact, and audit repository contracts. SQLite remains available for local development and deterministic unit tests.

The HTTP service provides public liveness/readiness endpoints, authenticated and authorized `/v1/runs` routes, correlation headers, structured errors, redacted operational events, and labeled metrics. Runtime settings select SQLite or PostgreSQL explicitly.

Docker and Compose manifests define a portable API/PostgreSQL deployment. Install `requirements/phase_7_1.txt` before local service tests; Docker is only required for container and PostgreSQL integration validation.
