# Phase 8.9.7 — Metals Risk-Aware Vehicle Constraints

## Objective

Apply deterministic, explainable pre-allocation constraints to Metals vehicles before the existing purchase-rounding layer executes.

## Preserved architecture

The universal purchase engine remains responsible for minimum purchase amounts, fractional eligibility, and purchase increments. This phase adds a Metals risk gate that produces a maximum allocation percentage and reason codes before those execution rules are applied.

## Inputs

- approval state
- metadata freshness
- average daily volume
- bid/ask spread
- expense ratio
- futures roll drag
- miner beta
- single-company concentration
- single-country concentration
- currency exposure
- tax structure
- portfolio overlap
- factor exposure score

## Outcomes

- `ELIGIBLE`: no active risk reductions; base allocation cap applies.
- `CAPPED`: vehicle remains investable but receives a lower deterministic cap.
- `BLOCKED`: allocation cap is zero and purchase is prohibited.

## Fail-closed rules

A vehicle is blocked when it is unapproved, has stale metadata, or uses an unknown, unverified, or disallowed tax structure. Multiple soft constraints use the lowest applicable cap.

## Operational command

```powershell
python scripts\publish_metals_risk_aware_constraints.py `
  --input config\metals\risk_aware_constraints_validation_sample.csv `
  --strict
```

Live operation defaults to:

```text
data\operations\metals\risk_aware_constraints_input.csv
```

An absent live input produces `NO_VEHICLES`; strict mode returns exit code 1.

## Outputs

Written under `data\operations\metals\risk_aware_constraints`:

- `metals_vehicle_constraint_summary.json`
- `metals_vehicle_constraints.json`
- `metals_vehicle_constraints.csv`

## Validation sample

The committed sample is deterministic test data and is not a portfolio recommendation. It demonstrates:

- IAU eligible at the base cap;
- SLV capped for portfolio overlap;
- COPX capped for beta, country, currency, and factor exposure;
- JJU blocked because it is unapproved, stale, and unverified.
