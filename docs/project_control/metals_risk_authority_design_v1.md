# Metals Risk Authority Design V1 — Read-Only Gate

Status: DESIGN AUDIT ONLY

This gate exists to determine whether the restored `risk` presentation family can be re-created from current UIP-owned Metals evidence without copying stale rows or claiming retired-methodology equivalence.

## Safety constraints

- No PostgreSQL writes.
- No presentation staging.
- No presentation activation.
- No central publisher schedule change.
- No restored/stale `risk` rows may be copied forward as fresh.
- Any new authority must be explicitly non-legacy-equivalent unless the retired methodology is fully recovered and independently certified.

## Questions this audit must answer

1. What exact historical payload/schema did the restored Metals `risk` rows expose?
2. What source/authority/run/model/version lineage is actually present on those rows?
3. Which risk quantities can be reproduced directly and transparently from current UIP-native Metals vehicle price history?
4. What observation windows and minimum-observation rules are defensible from the current native history?
5. Which historical fields cannot be reproduced honestly and therefore must remain absent or be replaced by explicitly new V1 semantics?
6. Can a new `UIP_NATIVE_METALS_RISK_V1` contract be defined without projecting vehicle semantics onto commodity authority?

## Required evidence

The audit should use only read-only evidence from:

- the restored active rich publication inventory/lineage;
- the current UIP-native Metals price-history authority;
- repository code/contracts that define existing Metals risk semantics, if any;
- current production artifacts or repository history where available.

## Expected decision outcomes

The audit must finish with exactly one of these decisions:

- `AUTHORIZE_UIP_NATIVE_METALS_RISK_V1_DESIGN`
- `DO_NOT_AUTHORIZE_RISK_V1_UNTIL_MISSING_SEMANTICS_ARE_GOVERNED`

A design authorization is not production authorization. A separate contract/builder rehearsal and production wiring gate would still be required.
