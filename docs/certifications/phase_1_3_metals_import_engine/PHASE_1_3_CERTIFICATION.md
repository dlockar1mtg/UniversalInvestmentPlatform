# Phase 1.3 — Metals Universal Import Engine Certification

## Certification Scope

This certification covers the complete integration path from the standalone
Metals Investment Intelligence Platform into the Universal Investment
Intelligence Platform.

## Certified Pipeline

1. Metals native analytics
2. Metals Universal Export Adapter
3. Universal Integration Package
4. Package discovery
5. SHA-256 integrity validation
6. Transactional import
7. Row-level lineage
8. Package and import audit records
9. Universal platform registry synchronization
10. Current-state views
11. Operational health reporting

## Certified Versions

- Metals platform: v8.1
- Metals Universal adapter: 1.2.2
- Universal contracts: v1
- Universal Import Engine: Phase 1.3

## Required Certification Result

The end-to-end certification must prove:

- A fresh package is created
- The package passes checksum validation
- Six Universal datasets are imported
- Exactly 62 package rows are loaded
- History-table counts grow by the expected amount
- Current-state views remain available
- Every imported row contains valid lineage
- The package is registered exactly once
- The successful import is audited
- The platform registry becomes ACTIVE
- The operational health status becomes HEALTHY

## Certification Command

    python scripts\certify_phase_1_3_6_metals_end_to_end.py --metals-root C:\Users\DevonLockard\metals

## Certification Decision

A PASS result certifies Metals as the first complete production integration of
the Universal Investment Intelligence Platform.
