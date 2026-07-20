# Phase 8.2 — Metals Official Provider Hardening Certification

## Certification decision

**PASS — the Metals official-provider layer is approved for production-hardening integration.**

Evaluation date: 2026-07-20

Branch: `phase-8-metals-production-hardening`

## Implemented capabilities

### Official providers

- EIA uranium weighted-average purchase price
- World Bank monthly commodity prices:
  - gold
  - silver
  - platinum
  - copper
  - aluminum
  - nickel
  - zinc
  - tin
- Existing universal FRED provider with a canonical twelve-series Metals catalog
- Existing universal Alpha Vantage market-quote provider retained as the production quote path

### Reliability controls

- Injectable HTTP transports
- Deterministic offline fixtures
- Request timeouts
- Configurable retry attempts
- Exponential backoff
- Maximum-age freshness enforcement
- Future-observation rejection
- Schema-signature validation
- Workbook and HTML validation
- Sanitized provider failures
- Provider-lineage enforcement
- Duplicate protection through universal ingestion
- Deterministic batch fingerprints
- Stable normalized Metals asset identifiers
- Current World Bank workbook discovery with a freshness-guarded fallback

## Live validation

### EIA

Status: PASS

Attempts: 1

Normalized record:

- Asset: `metals:uranium`
- Observation date: 2024-12-31
- Value: 50.36 USD per pound U3O8 equivalent
- Source: `EIA::URANIUM_WEIGHTED_AVG`
- Batch fingerprint: `12bf2face6b71c3577bd4b5ef4c67f12daeb47d0157204dddd878444a25a60f2`

### World Bank

Status: PASS

Attempts: 1

Observation date: 2026-06-01

Eight normalized records were produced for aluminum, copper, gold, nickel, platinum, silver, tin, and zinc.

Batch fingerprint:

`12653f8fcf4cc7d6a904bc9e3db6b17092831d5514c032cc93bc61c64a2a0464`

## Freshness-control evidence

The first World Bank live check reached a structurally valid legacy workbook ending in December 2024. The maximum-age policy rejected it rather than silently accepting stale values.

The endpoint was corrected and then hardened with current-workbook discovery plus a guarded fallback. The subsequent live check returned June 2026 observations and passed freshness validation.

This incident confirms that structural validity alone cannot certify provider data and that the Phase 8.2 freshness gate operates as designed.

## Automated validation

- Metals official-provider and policy tests: 16 passed
- Production test suite: 52 passed
- Full platform regression suite: 1,044 passed
- Non-blocking warnings: one existing FastAPI/Starlette deprecation warning
- Repository status: clean
- Blocking defects: none

## Security assessment

- No provider secrets are stored in source or configuration.
- EIA and World Bank require no API keys.
- FRED and Alpha Vantage continue to use environment-based secret handling.
- Provider exceptions do not expose internal transport details.
- Live health output contains public observations and fingerprints only.

## Completion decision

Phase 8.2 is complete. The legacy Metals collector implementations are superseded by the universal production provider layer.

Proceed to **Phase 8.3 — Metals Configuration and Asset Registry**.
