# Phase 5.4.3 — End-to-End Decision Orchestrator

Phase 5.4.3 executes one policy-controlled decision-to-execution run across the certified ranking and allocation engines.

- Executes decision adaptation, ranking, capital supply, sizing, constraints, objectives, optimization, and execution.
- Preserves immutable intermediate results and ordered stage records.
- Uses portfolio snapshots to construct current position, asset-class, and group constraint context.
- Quarantines opportunity-scoped invalid inputs while allowing valid opportunities to continue.
- Reports batch-fatal boundaries as failed orchestration results.
- Produces a deterministic output fingerprint and enforces capital conservation through execution.

The orchestrator coordinates existing engines; it does not duplicate their scoring or allocation logic.
