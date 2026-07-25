# Phase 8.9.3 — Metals Daily Market Overlay

## Objective

Create a daily market layer that compares each canonical Metals vehicle with its benchmark exposure and produces freshness, divergence, execution-quality, and alert outputs.

## Inputs

The collector joins:

- certified vehicle metadata from `config/metals/vehicle_market_metadata.csv`;
- daily vehicle prices;
- daily benchmark prices;
- expense ratios;
- average volume;
- median bid/ask spread;
- metadata effective dates.

## Benchmark mapping

- Gold vehicles: `GC=F`
- Silver vehicles: `SI=F`
- Platinum vehicles: `PL=F`
- Copper vehicles: `HG=F`
- Uranium vehicles: `URA`
- Reserve vehicle BIL: `^IRX`

## Analytics

For every vehicle, the overlay calculates:

- daily vehicle return;
- daily benchmark return;
- raw divergence;
- daily expense drag;
- expense-adjusted divergence;
- execution-quality score;
- market and metadata freshness;
- divergence status;
- alert severity.

## Alert thresholds

- Normal divergence: absolute adjusted divergence below 1.5 percentage points.
- Elevated divergence: 1.5 to below 3.0 percentage points.
- Extreme divergence: 3.0 percentage points or greater.
- Stale or future-dated evidence is always critical.

## Outputs

Runtime outputs are written under:

`data/operations/metals/daily_market_overlay`

Files:

- `current_overlay.json`
- `current_overlay.csv`
- `overlay_summary.json`

## Execution

```powershell
python scripts\collect_metals_daily_market_input.py
python scripts\publish_metals_daily_market_overlay.py --strict
```

## Definition of done

Phase 8.9.3 is complete when:

1. focused tests pass;
2. production tests pass;
3. full-platform tests pass;
4. all 11 vehicle observations collect successfully;
5. overlay output is current;
6. unexplained critical divergence is absent or explicitly investigated;
7. strict publication returns exit code zero;
8. runtime outputs remain ignored by Git.
