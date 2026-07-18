# Phase 5.3.4 — Allocation Constraint Engine

This engine evaluates minimum-purchase, maximum-position, asset-class, group,
liquidity, and reserve constraints before optimization. It calculates remaining
headroom from current exposure, distinguishes hard from soft policy, records
pass, binding, violation, and not-applicable outcomes, and returns effective
allocation bounds.

Hard constraints reduce feasible bounds. Soft constraints remain audit evidence
for the objective and explanation layers. An opportunity becomes ineligible when
its hard-constrained maximum cannot satisfy its effective minimum purchase.
