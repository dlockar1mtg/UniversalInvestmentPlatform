# Phase 6.5 — Deployment and Production Operations

Phase 6.5 adds deterministic release manifests, checksum-protected ordered schema migrations, required-secret and environment gates, production storage initialization, and readiness enforcement before traffic acceptance.

Operational tooling includes SQLite online backup, integrity verification, fail-closed restore, deterministic run/job diagnostics, and first-signal-wins graceful shutdown coordination. These framework-neutral contracts can support local services, containers, or managed deployment platforms.

## Operational sequence

1. Load and validate runtime configuration and secret references.
2. Verify the release manifest and artifact fingerprint.
3. Initialize durable storage and apply ordered migrations.
4. Require database and artifact-directory readiness.
5. Start API and worker processes only after readiness succeeds.
6. Back up and verify durable state before migrations or release rollback.
7. On shutdown, stop claims, drain active work, and close service traffic.
