# Phase 5.4.4 — Run Registry, Reproducibility, and Recovery

Phase 5.4.4 adds the control plane for safe orchestration execution.

- Canonical request fingerprints are independent of opportunity and position input order.
- Re-registering the same run is idempotent; changing immutable inputs under an existing run ID fails.
- Every attempt preserves its terminal result and ordered stage-checkpoint fingerprints.
- Completed runs are returned idempotently instead of allocating capital twice.
- Reproducibility verification records a new audit attempt and compares output and checkpoint fingerprints.
- Failed or interrupted runs recover from the atomic orchestration boundary, never from partial domain state.

`InMemoryRunRegistry` is the deterministic reference implementation. Durable storage can implement the same boundary later without changing orchestration semantics.
