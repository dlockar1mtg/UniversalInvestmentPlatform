# Phase 5.4.2 — Cross-Stage Adapters

Phase 5.4.2 provides deterministic decision-to-ranking and ranking-to-allocation handoffs.

- Identity, decision provenance, batch fingerprints, scores, tiers, and bounds are preserved.
- Adapters translate existing outputs without recalculating domain intelligence.
- Invalid opportunity payloads are quarantined individually with stable reason codes.
- Duplicate identifiers fail the batch boundary instead of producing ambiguous lineage.
- Input ordering cannot change the normalized adapter outputs.

Allocation bounds must be supplied as prior sizing evidence in `source_payload.allocation_bounds`.
