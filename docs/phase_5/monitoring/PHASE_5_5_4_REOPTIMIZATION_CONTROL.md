# Phase 5.5.4 — Reoptimization Trigger and Control Engine

Phase 5.5.4 converts drift and observed outcome evidence into controlled reoptimization dispositions.

- Aggregates watch, material, and critical evidence without recalculating upstream results.
- Applies stable severity precedence and configurable signal-count boundaries.
- Suppresses duplicate reoptimization while a cooldown is active.
- Preserves monitoring continuity through hysteresis after a prior material trigger.
- Allows unplanned activity and capital imbalance escalation to bypass cooldown.
- Produces explicit contributing and suppressed reason codes plus a deterministic decision fingerprint.

The engine recommends a new immutable orchestration run; it never mutates the certified source run.
