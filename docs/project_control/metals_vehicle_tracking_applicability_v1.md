# Metals Vehicle Tracking Applicability V1

## Objective

Define which registered Metals implementation vehicles require quantitative tracking-quality metrics and which are correctly classified as indirect exposures where tracking to a spot/futures commodity benchmark is not applicable.

This design implements the tracking policy already defined by `UIP_NATIVE_METALS_VEHICLE_EVIDENCE_V1` and does not create tracking measurements by itself.

## Exact registered universe

The ranking universe is limited to:

- Gold: GLD, IAU, SGOL
- Silver: SLV, SIVR
- Platinum: PPLT
- Copper: CPER, COPX
- Uranium: URA, URNM

BIL remains a reserve cash proxy and is outside commodity implementation ranking.

## Tracking-required vehicles

### Physical-backed vehicles

GLD, IAU, SGOL, SLV, SIVR, and PPLT must have state `AVAILABLE` before preferred-vehicle ranking can use their tracking-quality component.

Their benchmark must be a governed history for the corresponding commodity exposure:

- GLD / IAU / SGOL -> governed gold commodity benchmark;
- SLV / SIVR -> governed silver commodity benchmark;
- PPLT -> governed platinum commodity benchmark.

For each vehicle, a complete result requires the configured 252-session window and the governed fields required by `UIP_NATIVE_METALS_VEHICLE_EVIDENCE_V1`, including annualized tracking error and return correlation.

### Futures fund

CPER must have state `AVAILABLE`, but a spot-copper series is not sufficient authority for its tracking-quality score. CPER requires a separately governed copper futures-index benchmark appropriate to the fund's investment objective.

## Explicit indirect-exposure states

COPX, URA, and URNM are equity vehicles whose economic exposure is through mining or thematic equities rather than direct ownership of the underlying commodity.

Their governed tracking state is:

`NOT_APPLICABLE_INDIRECT_EXPOSURE`

No synthetic spot-commodity tracking error or correlation may be manufactured for these vehicles. The explicit N/A state satisfies the evidence-family state requirement but is not itself a favorable tracking score.

## Fail-closed rules

- A missing physical/futures benchmark cannot default to a peer benchmark.
- A spot commodity series cannot be substituted for CPER's required futures-index benchmark.
- Spot copper cannot be used as a tracking benchmark for COPX.
- Spot uranium cannot be used as a tracking benchmark for URA or URNM.
- `NOT_APPLICABLE_INDIRECT_EXPOSURE` is allowed only for vehicle types explicitly permitted by the parent evidence contract.
- Tracking values may not be copied from issuer marketing statistics unless separately governed as source evidence.
- Missing tracking evidence does not become zero, neutral, or average.

## Authorization boundary

This design does not collect benchmark data, calculate tracking metrics, create preferred-vehicle labels, publish presentation records, authorize allocation or execution, alter source schedules, or restore the central publication cron.

`preferred_vehicle_ranking_ready` remains `false` until a later evidence rehearsal resolves the required benchmark histories and tracking metrics for the seven direct/futures vehicles and validates the three explicit indirect-exposure states.
