# Phase 5.3.9 — Serialization and Dashboard Outputs

This component exposes deterministic allocation outputs as complete JSON and
fixed-column allocation, execution, and audit tables and CSV files. Schema
version `5.3.9` preserves capital totals, opportunity amounts, effective bounds,
utility, reason codes, explanations, scheduled purchases, retained cash, six
audit stages, and batch conservation evidence.

Decimals, dates, enums, tuples, and immutable mappings are normalized into
portable machine values without recalculating upstream allocation results.
