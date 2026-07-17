# Phase 5.2.4 — Composite Priority Scoring

Composite priority scoring converts the eight weighted ranking factors into a final portfolio-relative score. All penalties are explicit, named, nonnegative, and retained for audit. Conditional comparability receives the policy-defined penalty; additional governed penalties may be supplied without changing factor calculations.

Scores are floored at zero and mapped to `HIGHEST`, `HIGH`, `MEDIUM`, `LOW`, or `DEFERRED` tiers. Batch ordering is deterministic: final priority, confidence, decision score, action strength, asset identifier, then decision identifier. This phase assigns priority order but does not distribute capital or suppress opportunities.
