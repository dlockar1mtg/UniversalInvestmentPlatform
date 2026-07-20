# Phase 7.4 — Dashboard and Operational UX

Phase 7.4 adds a responsive same-origin dashboard at `/dashboard`, backed by authenticated read-only operational endpoints.

The dashboard reports service readiness, provider and portfolio configuration status, API request totals, redacted events, and request metrics. The HTML and static assets are public but contain no operational data. A viewer or operator API key is required for `/v1/dashboard/summary`, `/v1/dashboard/events`, and `/v1/dashboard/metrics`.

The browser keeps the entered key in `sessionStorage`, clears it after an authentication failure, and never writes it into HTML, URLs, logs, or persistent browser storage. Loading, authentication failure, empty activity, degraded readiness, and responsive mobile states are explicit.

Run the service with `python scripts/run_production_api.py`, then open `http://127.0.0.1:8000/dashboard` for local use.
