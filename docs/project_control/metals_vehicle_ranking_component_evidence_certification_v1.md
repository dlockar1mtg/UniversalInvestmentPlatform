# Metals Vehicle Ranking Component Evidence Certification V1

## Status

`METALS_VEHICLE_RANKING_COMPONENT_EVIDENCE_CERTIFIED`

This certification preserves the exact per-vehicle evidence already emitted by the successful read-only Metals Four-Factor Ranking V1 rehearsal. It does not recalculate rankings, authorize new preferred labels, or change production state.

## Pinned source

- authority: `UIP_NATIVE_METALS_VEHICLE_RANKING_V1`
- methodology: `1.2.0`
- rehearsal run: `34983030032`
- artifact id: `10402526066`
- artifact digest: `sha256:708a76c8defea92b89c30618608d802d6399b17309a6fed70d02358a5df5d015`
- `rehearsal.json` sha256: `e2499f90ade51d1f396af327ee196baaf46ad7522d88fc1228fa5c99b49705b7`
- risk csv sha256: `e44ffa3b57e55f0a36482db057fa6f4cf34d8f0cdf34cc67a6096d9feab59f09`
- ADV evidence sha256: `7ea64b5b975fea4c51c8fdb3e00fec83bcf1527e6b65a2eb2a23f64775913d65`

## Certified methodology weights

- exposure fidelity: 35%
- cost efficiency: 25%
- liquidity / implementation friction: 25%
- risk efficiency: 15%

## Certified evidence preserved per ranked vehicle

Where present in the rehearsal artifact, the certification preserves:

- total implementation score;
- exposure-fidelity score;
- cost-efficiency score;
- liquidity / implementation-friction score;
- risk-efficiency score;
- average dollar volume;
- bid/ask spread in basis points;
- expense ratio;
- annualized volatility;
- downside volatility;
- maximum drawdown magnitude;
- empirical 95% VaR.

Platinum / PPLT remains a singleton. The source rehearsal did not assign it a competitive total, cost, liquidity, or risk-efficiency score, so this certification does not invent those values. It preserves only the raw evidence emitted for the singleton plus its exposure-fidelity score.

## Certified ordering remains unchanged

- Gold: `GLD > SGOL > IAU`
- Silver: `SLV > SIVR`
- Platinum: `PPLT` only; no competitive leader
- Copper: `COPX > CPER`
- Uranium: `URA > URNM`

This evidence explains the already-certified ordering. It does not itself authorize presentation labels. Existing presentation authorization remains controlling for preferred-label semantics, including Silver suppression and Platinum singleton treatment.

## Presentation intent

The next bounded presentation step may consume this certification to explain why vehicles rank as they do, including the trade-offs between cost, liquidity, exposure structure, and risk. The browser must not recalculate scores or infer missing values.

Indirect exposure must remain explicit: COPX is miners-equity exposure; URA and URNM are thematic-equity exposure rather than direct physical commodity exposure.

## Non-authorizations

This certification does not authorize:

- production ranking writes;
- commodity recommendation changes;
- portfolio allocation;
- position sizing;
- automatic execution;
- source collection schedule changes;
- central publication cron restoration.
