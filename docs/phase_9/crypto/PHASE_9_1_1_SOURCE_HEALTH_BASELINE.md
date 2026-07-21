# Phase 9.1.1 — Crypto Source Health Baseline

## Evaluation date

2026-07-21

## Source project

- Source path: `C:\Users\DevonLockard\crypto`
- Source repository status: not a Git repository
- Current generation: v13.0.0
- Python version: 3.14.6
- Declared dependencies: DuckDB, pandas, PyYAML, requests, python-dotenv, scikit-learn, and joblib
- Dependency consistency: `python -m pip check` passed
- Live database: `data/crypto_intelligence.duckdb`

## Source scale

The live tree contains:

- 957 files;
- 343 Python files;
- 26 root-level `test_*.py` scripts;
- 55 DuckDB files;
- approximately 3.75 GB of database files;
- 64 package files across the package root, `ml`, and `optimization`.

Historical DuckDB snapshots account for nearly all source-tree size. They are evidence and recovery artifacts, not integration candidates.

## Test-system finding

The project has no pytest configuration or conventional test package. Running:

    python -m pytest --collect-only -q

reported zero collected tests. The apparent tests are standalone executable scripts. This is a robustness gap: they do not participate in normal automated test discovery.

Because several scripts execute schema and persistence operations, the baseline was run against an isolated source copy containing a disposable copy of the current database. The real `.env`, historical databases, caches, and logs were excluded.

## Isolated test result

A total of 43 standalone smoke and version-validation scripts were executed:

- PASS: 39
- FAILED: 4
- Live database modified: no
- Live database SHA-256 before and after: identical
- Network calls found in test scripts: none

All 18 historical smoke-test programs passed.

## Superseded predecessor failures

The four failures are historical predecessor assertions rather than evidence that the v13 implementation is unhealthy:

| Failed predecessor | Finding | Superseding evidence |
|---|---|---|
| `test_v8_1_0_compatibility.py` | Older scikit-learn elastic-net assertion no longer matches the installed API | `test_v8_1_1_stabilization.py` passed |
| `test_v8_2_1_module31_schema.py` | Expected the superseded Module 31 schema | `test_v8_2_2_module31_schema.py` passed against the actual schema |
| `test_v10_1_0_module39_schema.py` | Expected 18 columns; current schema has 19 | `test_v10_1_1_module39_schema.py` passed |
| `test_v12_0_0_module42_schema.py` | Expected the pre-guardrail recommendation schema | `test_v12_0_1_decision_guardrails.py` passed |

These scripts must be retained as historical evidence but must not become production gates. Their successor behavior should be converted into deterministic pytest regression tests during hardening.

## Additional health findings

1. The root README identifies v4.2 while the live system is v13.0.0.
2. Configuration contains policies for CoinGecko, Coinbase, Kraken, Binance, FRED, and Alternative.me that require consolidation with universal provider ownership.
3. Generic machine-learning and optimization implementations overlap universal platform capabilities.
4. The source tree contains a long chain of upgrades, installers, hotfixes, recovery tools, and database snapshots that must not be merged wholesale.
5. A real `.env` exists and is excluded from every audit and integration artifact.

## Assessment

The v13 source is sufficiently healthy for capability evaluation, but it is not yet approved for production integration.

The universal platform will not absorb the standalone application wholesale. Phase 9 will:

1. create a hash-traceable source inventory;
2. identify Crypto-specific provider, identity, market-structure, custody, liquidity, and decision capabilities;
3. replace duplicated infrastructure with universal services;
4. establish canonical export and semantic-parity contracts;
5. convert current-version behavior into discoverable offline tests;
6. require production-readiness and runtime-independence certification before merge.

## Initial disposition policy

- **Adapt:** Crypto-specific asset/provider/policy configuration after review.
- **Evaluate:** current source, integration surfaces, schemas, and behavioral scripts.
- **Replace:** generic ML and optimization with universal capability.
- **Archive:** historical upgrades, installers, recoveries, hotfixes, and backups.
- **Reference only:** release documentation and superseded behavioral evidence.

## Authorized next step

Run the repository-owned Crypto inventory audit, commit its generated evidence, and complete the component-level capability decision matrix before implementing production adapters.
