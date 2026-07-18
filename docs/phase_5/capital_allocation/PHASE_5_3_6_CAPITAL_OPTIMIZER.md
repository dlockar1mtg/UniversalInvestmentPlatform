# Phase 5.3.6 — Deterministic Capital Optimizer

The optimizer allocates deployable capital through three deterministic passes:
feasible minimum purchases, objective-ordered targets, and objective-ordered
hard maximums. Opportunities that cannot receive their full minimum are skipped
rather than assigned invalid partial purchases.

The optimizer preserves objective ordering, binding constraints, funding reason
codes, unmet capacity, unspendable quantum residuals, and total objective value.
Unavailable and reserved capital cannot be spent, and every result enforces
`gross = reserved + allocated + residual`.
