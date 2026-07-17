# Phase 5.2.1 — Portfolio Ranking Contracts

Phase 5.2 consumes immutable Phase 5.1 `DecisionResult` objects and ranks competing opportunities across the portfolio. This subphase defines contracts only; it does not calculate ranking factors or distribute capital.

The contracts separate decision quality from portfolio-relative priority through eight explicit factors: decision score, confidence, action strength, risk-adjusted opportunity, liquidity, diversification, portfolio capacity, and freshness. Default factor weights sum to 1.0 and remain policy governed.

Excluded opportunities are structured outcomes, never silently discarded. Ranked results require unique decisions and deterministic contiguous ranks beginning at one. Phase 5.2 cannot mutate Phase 5.1 decisions or exceed the single-decision allocation limits they contain.
