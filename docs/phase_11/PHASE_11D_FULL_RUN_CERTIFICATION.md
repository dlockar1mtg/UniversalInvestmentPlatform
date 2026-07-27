# Phase 11D — Universal Import and Full-Run Certification

Phase 11D imports the latest Metals, Crypto, and MTG delivery packages into the
central UIP DuckDB database.

The phase intentionally separates:

1. domain delivery completeness;
2. package freshness;
3. database import completeness;
4. MTG live-overlay completeness.

Metals and Crypto already publish the universal contract directly. The hosted
MTG package is converted through a privacy-preserving compatibility package and
the existing MTG universal adapter before import.

Run:

```powershell
python .\scripts\run_phase_11d_full_import.py
python .\scripts\run_uip_quick_output.py
```

The full-run report is written to:

`data/operations/phase_11/phase_11d/phase_11d_full_run_certification.json`
