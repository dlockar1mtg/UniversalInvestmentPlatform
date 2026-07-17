# Phase 5.2.2 — Ranking Eligibility and Comparability

Every Phase 5.1 decision becomes a structured `COMPARABLE`, `CONDITIONAL`, or `EXCLUDED` outcome before ranking. Expired decisions, blocked eligibility, non-opportunity actions, zero allocation capacity, severe staleness, and duplicate decision identifiers fail safely. Conditional eligibility and moderate staleness remain visible as conditional outcomes.

The engine never mutates its source decision and never silently discards an input. `HOLD` and `WAIT` can be enabled through a versioned profile but are excluded from capital-opportunity rankings by default.
