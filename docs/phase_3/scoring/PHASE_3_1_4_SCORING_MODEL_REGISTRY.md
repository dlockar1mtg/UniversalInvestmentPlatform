# Phase 3.1.4 — Scoring Model Registry

## Objective

Create a single source of truth that connects each asset class to a versioned scoring profile and normalization profile.

## Registry responsibilities

- Register model identity and version.
- Associate asset class, scoring profile, and normalization profile.
- Track draft, active, deprecated, and retired lifecycle states.
- Preserve effective-date windows.
- Resolve the correct model for a historical or current scoring date.
- Prevent duplicate registrations.
- Detect overlapping active version windows.
- Produce an auditable model-selection result.

## Resolution rules

1. Asset class must match.
2. Model must be active unless another lifecycle state is requested explicitly.
3. The requested date must fall within the effective window.
4. The latest effective version wins.
5. Ambiguous models require explicit `model_id`.
6. Historical scoring must resolve the model effective on the historical date.

## Initial configuration

The initial YAML registry contains draft entries for:

- Crypto
- ETF
- Metals
- MTG
- Housing
- Cash and cash equivalents

Models remain in draft status until their Phase 3.1.5 asset-class profiles are implemented and certified.
