# Universal Portfolio Engine

## Phase 2.1 — Portfolio Domain Model

This package defines the universal portfolio vocabulary used across all investment
platforms in the Universal Investment Intelligence Platform.

### Domain entities

- Portfolio
- Account
- Transaction
- Position
- Valuation
- AllocationTarget
- PortfolioSnapshot

### Design principles

1. Transactions are the auditable source of truth.
2. Positions are calculated outputs, not manually maintained facts.
3. Valuation provenance and confidence are retained.
4. Asset category is independent of instrument structure.
5. Portfolio targets are configuration-driven.
6. Contribution-only rebalancing is the initial default.
7. Alternative assets may use discrete purchase constraints and stale valuations.

### Phase boundary

Phase 2.1 defines and validates the domain. It does not yet calculate positions,
allocation drift, contribution recommendations, or rebalance actions.
