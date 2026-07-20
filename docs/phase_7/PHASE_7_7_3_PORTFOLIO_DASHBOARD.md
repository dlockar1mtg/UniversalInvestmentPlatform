# Phase 7.7.3 - Portfolio Dashboard and Historical UX

The authenticated operational dashboard now presents the latest persisted Neon portfolio snapshot and bounded history.

## States and projections

- Empty, loading, error, ready, and seven-day stale states are explicit.
- Market value, cost basis, gain/loss, and return are derived from exact persisted decimals.
- Allocation is grouped deterministically across MTG, ETF, metals, and crypto holdings.
- Positions retain identity, quantities, group, cost basis, market value, and gain/loss.
- History is summary-only and limited to ten snapshots in the dashboard.
- All provider and holdings text is HTML-escaped before rendering.
- The API key remains in session storage only and portfolio content is not cached locally.
- Tables scroll on small screens and flatten safely for printing.
