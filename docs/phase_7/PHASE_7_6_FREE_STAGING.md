# Phase 7.6 — Render Free, Neon Free, and Scheduled One-Shot Processing

This profile deploys the authenticated API and dashboard to a sleeping Render Free web service, stores durable state in an external TLS-only Neon PostgreSQL database, and replaces continuous worker processes with an idempotent GitHub Actions cycle every six hours.

The runtime consumes Render's assigned port and generated hostname, tolerates Neon cold starts with bounded connection retries, forbids hosted SQLite fallback, initializes both repository schemas idempotently, limits each scheduled cycle, prevents overlapping workflow runs, and keeps holdings and credentials out of Git and workflow artifacts.

This is authenticated personal staging, not an availability-guaranteed production service. Cold starts, delayed scheduled work, free-tier quotas, and limited restore history remain accepted constraints.
