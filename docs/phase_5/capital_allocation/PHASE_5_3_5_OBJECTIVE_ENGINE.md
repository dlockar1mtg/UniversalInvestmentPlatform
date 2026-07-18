# Phase 5.3.5 — Allocation Objective Engine

This engine calculates the auditable utility values used by the capital
optimizer. It combines ranking priority, sizing conviction, target-gap value,
diversification benefit, liquidity, and capital efficiency using policy weights
that must sum to one.

Soft binding and violation penalties are explicit and capped. Hard-ineligible
opportunities receive zero utility. Every raw score, weight, weighted
contribution, constraint penalty, and deterministic ordering key is preserved.
