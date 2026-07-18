# Phase 5.3.1 — Capital Allocation Contracts

Phase 5.3 begins with immutable contracts for capital pools, allocation bounds,
ranking-derived requests, policy constraints, allocation lines, statuses, reason
codes, and capital-conserving batch results. These contracts preserve the Phase
5.2 ranking handoff without performing sizing or optimization calculations.

All monetary values use `Decimal`. Capital results require both batch-level
conservation and agreement between the allocated total and allocation-line sum.
