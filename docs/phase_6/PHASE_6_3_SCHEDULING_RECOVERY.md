# Phase 6.3 — Scheduling, Idempotency, and Recovery

Phase 6.3 adds a durable SQLite job boundary for scheduled production decision runs. Jobs are ordered deterministically, registered through conflict-sensitive idempotency keys, and claimed atomically with exclusive worker leases.

Execution supports bounded exponential retry, durable error evidence, dead-letter disposition, owner-only completion, and deterministic recovery of expired worker leases. The worker function remains transport-independent so later process, container, or managed-queue workers can preserve identical lifecycle behavior.
