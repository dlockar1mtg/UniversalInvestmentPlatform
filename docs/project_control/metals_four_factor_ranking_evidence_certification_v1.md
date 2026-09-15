# Metals Four-Factor Ranking Evidence Certification V1

## Purpose

Certify the exact output of the first bounded, read-only Metals four-factor ranking rehearsal without authorizing publication of live preferred-vehicle labels.

## Certified source run

- workflow: `Metals Four-Factor Ranking V1 Rehearsal`
- run id: `34983030032`
- event: `workflow_dispatch`
- branch: `main`
- exact head: `1949dd03b4dd0d993b175763e44dd005c9e0d5a7`
- conclusion: `success`
- artifact: `metals-four-factor-ranking-v1-34983030032`
- artifact id: `10402526066`
- artifact digest: `sha256:708a76c8defea92b89c30618608d802d6399b17309a6fed70d02358a5df5d015`

The rehearsal consumed the pinned certified Metals production artifact from run `34849676771`, artifact id `10349591580`, digest `sha256:8c15699f4fa89f53039b4d1c4a5ea06882e7a9ea4ece4c1c984b69d7ae8edb7f`.

## Certified methodology

Ranking authority: `UIP_NATIVE_METALS_VEHICLE_RANKING_V1`

Methodology version: `1.2.0`

Weights:

- exposure fidelity: 35%
- cost efficiency: 25%
- liquidity / implementation friction: 25%
- risk efficiency: 15%

The rehearsal used certified recurring-cost evidence, certified 20-session Alpaca SIP spread evidence, governed 30-session ADV derived from the pinned production artifact, and Vehicle Risk V1 methodology `1.0.2` derived from the same pinned artifact.

## Certified read-only ordering

| Commodity | Certified order | Leader / state |
| --- | --- | --- |
| Gold | GLD > SGOL > IAU | GLD |
| Silver | SLV > SIVR | SLV |
| Platinum | PPLT | `ONLY_REGISTERED_IMPLEMENTATION` |
| Copper | COPX > CPER | COPX |
| Uranium | URA > URNM | URA |

Exact total scores:

- GLD: `85.48544649732895`
- SGOL: `77.88981280050356`
- IAU: `73.67619141270399`
- SLV: `89.53498202268918`
- SIVR: `88.48041654419333`
- COPX: `80.070548441811`
- CPER: `76.77609981066686`
- URA: `84.25`
- URNM: `60.9395767763326`

PPLT is not assigned a competitive score because Platinum has only one registered implementation vehicle.

## Safety certification

The source run explicitly proved:

- ranking rehearsal complete: true;
- preferred vehicle labels authorized: false;
- publication write performed: false;
- production state modified: false;
- allocation created: false;
- position sizing created: false;
- automatic execution authorized: false;
- central publication cron restored: false.

## Certification decision

`METALS_FOUR_FACTOR_RANKING_EVIDENCE = CERTIFIED`

This certifies the ordering and source provenance only. It does not itself authorize publication of `PREFERRED_IMPLEMENTATION_CANDIDATE` labels. Publication remains a separate governed step and must still respect the upstream commodity-actionability gate and presentation-contract audit.
