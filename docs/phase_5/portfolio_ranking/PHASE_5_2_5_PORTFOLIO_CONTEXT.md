# Phase 5.2.5 — Portfolio Context and Diversification Intelligence

This layer calculates portfolio-relative ranking inputs without duplicating the Phase 5.3 Universal Risk Engine. It evaluates current asset and asset-class exposure, target gaps, maximum-weight headroom, correlation benefit, diversification contribution, capacity, and concentration pressure.

The engine returns an immutable result and can create an enriched copy of `PortfolioRankingInput`; it never mutates the Phase 5.1 decision. Capacity uses the most restrictive asset or asset-class headroom. Diversification combines correlation, target-gap, and asset-class headroom scores through a versioned profile.
