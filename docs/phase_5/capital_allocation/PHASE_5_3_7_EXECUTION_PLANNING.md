# Phase 5.3.7 — Contribution and Execution Planning

This component translates optimized amounts into deterministic purchase,
deferral, and retained-cash instructions. Policy can execute capital immediately
or split it into exact weekly or monthly installments while preserving cents,
end-of-month dates, optimizer order, funding statuses, and reason codes.

Purchase instructions must sum exactly to optimized allocated capital. Residual
capital is represented explicitly as held cash, and zero-funded opportunities
remain visible as deferred instructions.
