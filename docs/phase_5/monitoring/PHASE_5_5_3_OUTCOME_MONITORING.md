# Phase 5.5.3 — Outcome and Allocation Monitoring

Phase 5.5.3 reconciles certified allocation plans with observed execution and position outcomes.

- Measures planned-versus-executed allocation variance.
- Reconciles post-execution positions against baseline positions plus observed purchases.
- Preserves target shortfalls and objective deterioration as explicit reason codes.
- Detects missing, under-, over-, and unplanned execution activity.
- Measures protected-capital, residual-cash, and total observed capital variance.
- Selects latest observations deterministically and produces a stable result fingerprint.

The engine reports observed outcomes without mutating the certified allocation plan.
