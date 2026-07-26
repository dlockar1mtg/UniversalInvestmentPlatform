# Phase 6 — Cross-Domain Capital Allocation Foundation

## Purpose

Make UIP the sole authority for scheduling, orchestration, and monthly capital allocation across MTG, metals, crypto, stocks/ETFs, and cash.

## Core policy

- Domain platforms publish certified opportunities and constraints.
- UIP validates each domain package before use.
- Incomplete or uncertified domains are excluded rather than guessed.
- No domain has a guaranteed monthly allotment.
- One domain may receive the entire monthly budget when it has the only qualifying opportunity.
- Cash may receive the entire budget when no opportunity clears policy.
- Whole-unit and minimum-allocation constraints are respected.
- Scheduling remains disabled until all required adapters are production-certified.

## Contract

Input schema: `uip-domain-opportunity-v1`.

Each package assigns both `allocation_authority` and `scheduling_authority` to `UIP` and provides domain status, certified opportunities, allocation increments, maximum allocation, holdings context, and assigned carry-forward funds.

## Allocation output

The allocation plan records:

- total monthly budget;
- deployable budget;
- invested amount;
- cash allocation;
- domain totals;
- selected opportunities;
- whole-unit counts;
- excluded domains;
- policy and reason codes.

## Current scope

This phase establishes the deterministic allocator and contract validation. It does not invoke or modify Crypto, Metals, MTG, or future Stocks workflows. Domain orchestration and scheduling activation occur only after their adapters are certified.
