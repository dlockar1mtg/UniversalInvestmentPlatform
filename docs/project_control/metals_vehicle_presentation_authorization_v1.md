# Metals Vehicle Presentation Authorization V1

## Purpose

Authorize the presentation-layer use of already-certified Metals vehicle ranking evidence without allowing the vehicle ranking to override the upstream commodity thesis.

This authority governs **display semantics only**. It does not create a new commodity recommendation, write a production ranking table, allocate capital, size a position, or execute a trade.

## Certified inputs

### Vehicle ranking evidence

- authority: `UIP_NATIVE_METALS_VEHICLE_RANKING_EVIDENCE_V1`
- methodology: `UIP_NATIVE_METALS_VEHICLE_RANKING_V1` version `1.2.0`
- rehearsal run: `34983030032`
- artifact id: `10402526066`
- artifact digest: `sha256:708a76c8defea92b89c30618608d802d6399b17309a6fed70d02358a5df5d015`

Certified ordering:

- Gold: `GLD > SGOL > IAU`
- Silver: `SLV > SIVR`
- Platinum: `PPLT` only
- Copper: `COPX > CPER`
- Uranium: `URA > URNM`

### Upstream commodity state

- authority: `UIP_NATIVE_METALS_TACTICAL_STATE_V1`
- methodology version: `1.0.0`
- production run: `34849676771`
- artifact id: `10349591580`
- artifact digest: `sha256:8c15699f4fa89f53039b4d1c4a5ea06882e7a9ea4ece4c1c984b69d7ae8edb7f`
- tactical-state output SHA-256: `615757072a8efc23b4553870abc439583e6a8723bdad4f286c3e991f33e19b0e`

The exact current upstream states relevant to registered implementations are:

| Commodity | Recommendation | Tactical state | 12m adjusted expected return |
| --- | --- | --- | ---: |
| Gold | STRONG_BUY | TACTICAL_SUPPORTIVE | 0.0826327744 |
| Silver | REDUCE | TACTICAL_DEFENSIVE | -0.0697335512 |
| Platinum | BUY | TACTICAL_SUPPORTIVE | 0.0577360512 |
| Copper | STRONG_BUY | TACTICAL_SUPPORTIVE | 0.1131678848 |
| Uranium | STRONG_BUY | TACTICAL_SUPPORTIVE | 0.305 |

## Actionability gate

A live `PREFERRED_IMPLEMENTATION_CANDIDATE` label may be shown only when all of the following are true:

1. certified vehicle ranking evidence exists for the commodity group;
2. the upstream commodity recommendation is `BUY` or `STRONG_BUY`;
3. the upstream tactical state is `TACTICAL_SUPPORTIVE`;
4. the commodity has at least two registered implementation vehicles;
5. the presentation consumes the canonical commodity identity through the governed Metals identity bridge;
6. no missing or conflicting required state exists.

Anything outside that intersection fails closed.

## Authorized presentation states

### Gold

- upstream: `STRONG_BUY`, `TACTICAL_SUPPORTIVE`
- certified order: `GLD > SGOL > IAU`
- authorized preferred implementation: **GLD**
- live label: `PREFERRED_IMPLEMENTATION_CANDIDATE`

### Copper

- upstream: `STRONG_BUY`, `TACTICAL_SUPPORTIVE`
- certified order: `COPX > CPER`
- authorized preferred implementation: **COPX**
- live label: `PREFERRED_IMPLEMENTATION_CANDIDATE`

This remains an implementation choice inside an already-positive Copper thesis. The miners-equity structure of COPX remains visible and must not be relabeled as direct physical or futures copper exposure.

### Uranium

- upstream: `STRONG_BUY`, `TACTICAL_SUPPORTIVE`
- certified order: `URA > URNM`
- authorized preferred implementation: **URA**
- live label: `PREFERRED_IMPLEMENTATION_CANDIDATE`

### Platinum

- upstream: `BUY`, `TACTICAL_SUPPORTIVE`
- registered implementation universe: `PPLT` only
- live label: `ONLY_REGISTERED_IMPLEMENTATION`
- no preferred-ranking claim is made because there is no peer vehicle in the registered universe.

### Silver

- upstream: `REDUCE`, `TACTICAL_DEFENSIVE`
- certified order: `SLV > SIVR`
- vehicle evidence may be displayed as informational implementation research;
- **no** `PREFERRED_IMPLEMENTATION_CANDIDATE` label is authorized;
- the presentation must retain the defensive Silver recommendation prominently enough that the vehicle ordering cannot reasonably be read as a buy instruction.

## Identity boundary

The certified raw tactical sidecar contains the historical doubled commodity prefix form such as `metals:commodity:metals:commodity:gold`. This authorization does **not** normalize those source rows in place.

The dashboard/read-model path must use the already-governed Metals presentation identity bridge to resolve canonical commodity identities. Incidental source-ID normalization remains prohibited.

## Presentation requirements

For an authorized multi-vehicle commodity, the detail surface should show:

- the upstream commodity recommendation and tactical state first;
- a `Ways to invest in <commodity>` implementation section beneath the commodity thesis;
- registered vehicle ticker, name, exposure type, recurring cost, liquidity/friction evidence, vehicle Risk V1 evidence, and certified implementation score where available;
- the preferred implementation label only for the exact authorized leader;
- rationale that explains the component trade-offs instead of exposing only an opaque total score;
- indirect-exposure caveats for miners/thematic-equity vehicles.

For defensive Silver, the same implementation section may be shown for research context, but the preferred label is suppressed.

## Explicit non-authorizations

This authority does not authorize:

- changing any commodity recommendation or tactical state;
- production ranking writes;
- cross-commodity ranking;
- portfolio allocation;
- position sizing;
- automatic execution;
- changing source collection schedules;
- restoring the central rich-publication cron.

The central publication cron remains paused.

## Next gate

After this authorization contract passes CI and merges, wire the contract into the presentation read model and dashboard detail surface in a separate PR. That implementation must be tested against Gold, Silver, Platinum, Copper, and Uranium semantics before any production rich publication is considered.
