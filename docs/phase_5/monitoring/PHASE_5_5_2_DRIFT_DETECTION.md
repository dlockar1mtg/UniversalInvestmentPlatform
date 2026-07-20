# Phase 5.5.2 — Drift Detection Engine

Phase 5.5.2 compares immutable monitoring baselines with the latest scoped observation evidence.

- Supports absolute, increase-only, and decrease-only directional drift.
- Supports absolute deltas and relative rates, including deterministic zero-baseline behavior.
- Classifies inclusive watch, material, and critical threshold boundaries.
- Selects the latest metric observation with stable timestamp and identifier tie-breaking.
- Preserves missing baseline and observed metric evidence without inventing values.
- Produces stable signal ordering and a deterministic detection fingerprint.

The engine detects and classifies drift only. Reoptimization decisions remain outside this component.
