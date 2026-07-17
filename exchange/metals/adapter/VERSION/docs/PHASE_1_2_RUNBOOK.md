# Phase 1.2 Runbook

## 1. Extract the bundle

Extract this ZIP anywhere outside the Universal repository.

## 2. Install from the Universal repository root

```bat
cd C:\Users\DevonLockard\InvestmentPlatform
python C:\path\to\Phase_1_2_Metals_Universal_Export_Adapter\scripts\install_phase_1_2_metals_adapter.py
```

## 3. Confirm dependencies

```bat
python -c "import pandas, duckdb; print('Dependencies OK')"
```

## 4. Build the export

```bat
python scripts\run_metals_universal_export.py --metals-root C:\Users\DevonLockard\metals
```

The output is written to:

```text
data\integration\metals\<package-id>\
data\integration\metals\latest\
```

## 5. Inspect

```bat
start data\integration\metals\latest\package_summary.json
start data\integration\metals\latest\export_manifest.csv
start data\integration\metals\latest\recommendations.csv
start data\integration\metals\latest\portfolio_positions.csv
```

The command must finish with `METALS UNIVERSAL EXPORT: PASS`. A failure means the package was rejected because a source file, source view, contract, or required value did not satisfy the certified boundary.

## 6. Git checkpoint

```bat
git status
git add exchange\metals scripts\run_metals_universal_export.py
git commit -m "Build Phase 1.2 Metals universal export adapter"
git tag uiip-phase-1.2-metals-export-adapter
```

Do not commit generated integration packages unless your repository policy explicitly retains certified snapshots.
