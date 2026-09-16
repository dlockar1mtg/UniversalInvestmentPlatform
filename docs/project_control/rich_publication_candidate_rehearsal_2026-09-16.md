# Rich Publication Candidate Rehearsal — 2026-09-16

## Exact rehearsal

- workflow: `Rich Publication Candidate Rehearsal`
- run id: `35101909242`
- run number: `4`
- event: `workflow_dispatch`
- head sha: `13bf9aea279cee48ebf36f04ab74adc79b416f17`
- conclusion: `success`
- artifact id: `10449025952`
- artifact digest: `sha256:ab7141edf812af764208fc59f795f4a50383d3934cc5850579f11bb827b3b094`
- candidate status: `UIP_RICH_PUBLICATION_CANDIDATE_REHEARSAL_PASS`
- candidate record count: `14249`
- candidate content fingerprint: `6c2820a663616a73399071af7a05c122dae4916a95bb666995ccaad521364e2a`

## Source evolution from prior certified rehearsal

Compared with rehearsal run `34996790272` / artifact `10407917628`:

- previous record count: `14238`
- current record count: `14249`
- delta: `+11`
- previous `metals_price_history`: `8547`
- current `metals_price_history`: `8558`
- all other certified Metals rich-family counts are unchanged.

The current rehearsal consumed Metals package `gha-34999326079`, produced by successful scheduled `Metals Production Cycle` run `34999326079`. The prior rehearsal consumed Metals package `gha-34878718916`.

The entire candidate-count increase is attributable to eleven additional certified `metals_price_history` records. No additional `metals_vehicle_implementation` records were created; that family remains exactly `10`.

## Production pin authorization boundary

A production publication may be updated to the exact rehearsed inputs only by changing:

- `EXPECTED_METALS_RUN_ID` to `34999326079`; and
- `EXPECTED_RICH_RECORD_COUNT` to `14249`.

This evidence does not authorize:

- automatic publication scheduling;
- central cron restoration;
- portfolio allocation;
- position sizing;
- automatic execution;
- source collection schedule changes; or
- any change to commodity recommendations or vehicle ordering.
