# UIP R3 Governance and Domain Review Standard

Status: `R3_GOVERNANCE_STANDARD_ACTIVE`

Milestone: `UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW`

## Purpose

R3 determines whether the exact refreshed outputs certified in R2 are sufficiently current, coherent, explainable, lineage-complete, and domain-faithful to be considered decision-ready inputs for later UIP portfolio intelligence.

R3 is not a generic data-quality gate. It exists in service of the UIP charter objective: improve long-term net-worth growth through explainable, evidence-based, risk-aware decisions while preserving uncertainty, source authority, and final human control.

R3 does not certify future predictive accuracy merely because outputs appear plausible. Predictive accuracy requires point-in-time outcome tracking, backtesting, walk-forward evaluation, champion/challenger evidence, and later model-performance governance.

## Governing authorities

R3 is subordinate to, and must remain consistent with:

1. `docs/project_control/01_PROJECT_CHARTER.md`;
2. `docs/project_control/03_ARCHITECTURE_AND_DATA_FLOW.md`;
3. `docs/project_control/04_ACTIVE_ROADMAP.md`;
4. `docs/project_control/05_PROJECT_STATE.md`;
5. `docs/project_control/06_CHANGE_LEDGER.md`;
6. `docs/project_control/R2_REFRESHED_DATA_REHEARSAL_CLOSEOUT.md`;
7. `docs/project_control/generated/r2_refreshed_data_rehearsal/r2_refresh_rehearsal_certification.json`;
8. certified MTG, Metals, and Crypto domain contracts, standards, and source-domain evidence.

Where UIP governance and a source-domain implementation appear to conflict, R3 must fail closed and route the issue for governance/domain investigation rather than silently choose one interpretation.

## Project-purpose alignment

R3 must help establish whether UIP can safely use each domain when later answering questions such as:

- What changed?
- What requires attention?
- Is this asset/domain outlook credible enough to consider?
- Should new capital be considered for this domain?
- Should existing capital remain, be reduced, or eventually rotate?
- Is cash retention preferable because available evidence is weak or risk is elevated?

R3 must not itself decide cross-domain capital allocation.

## Authority boundary

### Native authority first

Each domain retains authority over its own:

- asset identity and universe rules;
- source/provider authority;
- forecast methodology;
- model outputs;
- native risk semantics;
- native ranking semantics;
- recommendation semantics;
- missingness semantics;
- refresh/retraining distinctions;
- recertification rules.

R3 may evaluate whether outputs comply with those native rules. R3 may not redefine them.

### UIP authority

UIP may evaluate:

- certified-output freshness and completeness;
- internal coherence;
- obvious anomalies and distribution pathologies;
- change-from-prior plausibility;
- semantic preservation across integration;
- lineage completeness;
- whether evidence is sufficient for later portfolio use;
- routing of suspicious findings.

### Prohibited authority

R3 may not create or imply:

- universal cross-asset ranking;
- universal risk-score normalization;
- universal forecast-score normalization;
- cross-domain allocation weights;
- execution-ready purchase authority;
- automatic purchase/trade execution;
- fabricated values for missing authority;
- claims of predictive accuracy unsupported by outcome validation.

## R3 review dimensions

Every domain must be reviewed across all seven governed dimensions.

### 1. Freshness and completeness

Question:

`Is the certified evidence current enough for its native use case, and are expected governed outputs present without silently filling unsupported gaps?`

Review examples:

- source and package timestamps;
- freshness status from R2;
- expected dataset families present;
- current-price or market-observation coverage;
- provider/readiness state;
- explicit governed gaps distinguished from failures.

A governed missing value is not automatically a defect.

### 2. Native self-consistency

Question:

`Do outputs agree with the domain's own rules and with one another?`

Review examples:

- recommendation labels compatible with native evidence;
- rank/rank-type consistency;
- forecast availability flags consistent with forecast values;
- risk labels/scores consistent with native contract;
- investment-vehicle/benchmark identity consistency;
- no impossible state combinations.

### 3. Distribution and outlier review

Question:

`Do output distributions contain suspicious, impossible, structurally broken, or extreme values requiring investigation?`

R3 must distinguish:

- mathematically/statistically unusual values;
- native-domain legitimate extremes;
- data or model pathologies.

No generic universal threshold may be imposed unless already governed for that domain.

### 4. Change-from-prior plausibility

Question:

`Are changes from prior certified evidence explainable and proportionate to underlying source/model changes?`

Review examples:

- sudden recommendation flips;
- large forecast revisions;
- large price moves;
- rank movement;
- risk-state shifts;
- universe changes.

Large changes are not automatically failures. Unexplained large changes require review or domain investigation.

### 5. UIP semantic preservation

Question:

`Did UIP preserve source meaning, missingness, lineage, and domain-specific semantics without silently reinterpreting outputs?`

This dimension must verify the integration contract rather than reinterpret the model.

### 6. Decision readiness

Question:

`Is this domain's certified output sufficiently current, coherent, explained, and supported to be considered in later UIP portfolio decision logic?`

Decision readiness does not mean:

- guaranteed accuracy;
- direct execution permission;
- cross-domain superiority;
- allocation authorization.

A domain can be decision-ready while retaining governed gaps, provided those gaps are explicit and do not invalidate the permitted decision use.

### 7. Investigation routing

Question:

`If something is suspicious, where must it be investigated and what downstream use must be restricted until resolved?`

Routing rules:

- source/model defect -> owning native domain;
- UIP mapping/import/lineage defect -> UIP;
- ambiguous cross-system defect -> primary correction owner plus UIP reference;
- unresolved material anomaly -> exclude affected evidence from later decision logic until recertified.

## Allowed R3 findings

### `PASS`

Use only when:

- all seven dimensions pass;
- no material unresolved anomaly exists;
- all meaningful gaps are within already-certified native behavior;
- lineage and semantic preservation are complete;
- evidence is suitable for later portfolio consideration.

### `PASS_WITH_GOVERNED_GAPS`

Use when:

- the domain is decision-ready for a bounded use;
- one or more explicit native/governed gaps remain;
- missing authority is preserved rather than synthesized;
- the gaps are documented and do not invalidate the permitted use.

### `REVIEW`

Use when:

- evidence is suspicious or insufficient for decision-readiness determination;
- a material anomaly requires human/domain review;
- no confirmed native defect has yet been established.

A `REVIEW` finding blocks affected evidence from later decision logic until resolved or explicitly bounded.

### `DOMAIN_INVESTIGATION_REQUIRED`

Use when:

- evidence supports a likely source/model/native-domain defect;
- native semantics appear violated;
- a material unexplained output change cannot be reconciled;
- downstream UIP compensation would be inappropriate.

The affected domain or evidence must remain excluded from later decision logic until source-domain investigation and recertification are complete.

## Domain-specific review standards

## MTG

R3 must preserve the certified three-lane model:

- Collector;
- Pre-Collector;
- Secret Lair.

Required semantic rules:

- native rank must remain attached to native rank type;
- native rank is not a universal MTG rank or cross-asset rank;
- `BUY_CANDIDATE_NOW` remains `MODEL_QUALIFIED_ENTRY_CANDIDATE`, not execution-ready purchase authority;
- manual execution-price validation remains required where governed;
- Secret Lair remains a dynamic universe;
- missing current price remains missing;
- missing forecast remains missing;
- missing rank remains missing;
- missing purchase status remains missing;
- no missing authority may be converted to zero, worst rank, or WAIT.

R2-specific evidence to review:

- 968 native-authority rows;
- 50 Collector rows;
- 131 Pre-Collector rows;
- 787 Secret Lair rows;
- 161 certified fresh-price rows;
- 49 certified fresh-decision rows;
- 807 governed baseline-fallback rows.

The 807 fallback rows are not automatically a failure. R3 must characterize whether fallback use is transparent, valid under native authority, and sufficient for the intended later decision use.

R3 must use certified MTG source standards/contracts as authority for lane behavior, recommendation semantics, ranking semantics, evidence sufficiency, and dynamic-universe behavior.

## Metals

R3 must preserve the distinction among:

- commodity/benchmark intelligence;
- registry assets;
- investable vehicles;
- reserve/noncommodity assets;
- native forecasts and recommendations.

Required semantic rules:

- commodity benchmarks are not silently converted into direct investment vehicles;
- unsupported liquidity, market/region, or historical authority is not synthesized;
- missing forecast authority remains NULL/missing;
- native recommendation labels remain native evidence;
- vehicle constraints and provider authority remain domain-specific;
- no cross-domain weighting is inferred from Metals outputs.

R2-specific evidence to review:

- 10 registry assets;
- 11 vehicles;
- 11/11 current market vehicles;
- 9 official-provider records;
- production readiness PASS;
- 62 imported rows;
- zero daily-market critical alerts at R2 closeout.

R3 must distinguish a benchmark outlook from an investable-vehicle decision and must not collapse those concepts.

## Crypto

R3 must preserve the certified Crypto native contract and UIP mapping boundary.

Required semantic rules:

- current certified universe remains source-defined, not permanently hard-coded by R3;
- native `WAIT` maps to universal `watch` only at the certified UIP integration boundary;
- native `AVOID` maps to universal `sell` only at that boundary;
- unknown native recommendation labels fail closed;
- absent holdings remain absent and are not synthesized as positions;
- native risk semantics remain native and are not converted into a universal risk score;
- no cross-asset ranking or allocation inference is permitted.

R2-specific evidence to review:

- 43 active modules passed;
- 6 asset-master rows;
- 132 forecasts;
- 6 recommendations;
- 6 risk records;
- 1 platform-status row;
- 0 portfolio-position rows;
- 151 disposable UIP imported rows;
- market data current through 2026-08-15 at R2 execution;
- macro data current through 2026-08-14 at R2 execution;
- source database unchanged;
- supported populated-database incremental refresh (`full_refresh=false`) used without a paid CoinGecko key.

R3 must not treat the governed incremental-refresh correction as a defect merely because the original R2 plan requested an empty-state full refresh.

## Evidence requirements

Every R3 domain finding must retain:

- domain ID;
- exact R2 evidence authority;
- source commit/version or native boundary;
- data-as-of/freshness evidence;
- dimensions reviewed;
- checks performed;
- observed anomalies;
- governed gaps;
- finding;
- decision-readiness scope;
- prohibited downstream uses;
- investigation owner when applicable;
- lineage pointers.

## Decision-readiness principle

R3 certifies whether evidence is fit to enter later decision methodology, not what the final portfolio action should be.

A domain is decision-ready only when UIP can explain:

- what evidence is current;
- what is missing;
- what the native model is saying;
- how uncertain that evidence is;
- whether material anomalies remain;
- what source/lineage supports the result;
- what the result is and is not authorized to mean.

## Predictive-accuracy boundary

R3 must never use visual plausibility, reasonable-looking distributions, or agreement with current market intuition as proof of forecast accuracy.

Predictive/model performance requires separate governed evidence based on:

- point-in-time historical data;
- anti-lookahead controls;
- survivorship controls;
- walk-forward testing;
- realized outcome comparison;
- benchmark/counterfactual comparison where appropriate;
- champion/challenger evaluation;
- material-degradation review and rollback.

R3 may identify whether those performance authorities exist, but may not invent them.

## Cross-domain boundary

R3 must not compare native domain outputs on a shared score merely because fields appear numerically comparable.

Examples of prohibited R3 inference:

- declaring a 20% MTG forecast superior to a 15% Crypto forecast solely from percentages;
- comparing a Metals native risk label directly with a Crypto native risk score as though they share one calibrated scale;
- using native rank numbers across MTG lanes or across asset classes as a common rank;
- converting domain recommendations into portfolio weights.

Any future cross-domain comparison, ranking, or allocation methodology requires separate governance and empirical validation.

## R3 implementation gate

No R3 evaluation harness may be certified until it demonstrates that:

- this standard is used as the controlling contract;
- all seven dimensions are represented;
- domain-specific checks are separate from universal checks;
- no native threshold is invented in UIP;
- governed gaps remain explicit;
- suspicious findings can fail closed;
- findings map only to the four authorized R3 findings;
- decision-readiness scope and prohibited uses are explicit;
- no cross-asset ranking, allocation, or execution authority is created.

## R3 sequence

1. establish and review this governance/domain standard;
2. implement the R3 evidence schema and fail-closed review harness;
3. validate the harness against certified R2 evidence without changing domain outputs;
4. execute Crypto review;
5. execute Metals review;
6. execute MTG review;
7. reconcile domain findings into R3 closeout evidence;
8. route any `REVIEW` or `DOMAIN_INVESTIGATION_REQUIRED` finding before permitting affected evidence into later decision logic;
9. only after R3 closeout proceed to the next governed milestone.

## R3 principle

> R3 exists to determine whether certified domain intelligence is trustworthy enough, within its native meaning and known uncertainty, to enter later UIP portfolio decision methodology. It must preserve domain authority, expose gaps and anomalies, maintain lineage, and refuse to manufacture comparability, accuracy, or execution authority that has not been separately governed and empirically validated.
