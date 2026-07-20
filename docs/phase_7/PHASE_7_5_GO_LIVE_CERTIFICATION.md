# Phase 7.5 — Staging, Security, and Go-Live Certification

Phase 7.5 adds the controlled boundary between a production-capable repository and a live deployment. It supplies production HTTP hardening, a staging Compose overlay, placeholder-only environment configuration, a manually authorized GitHub go-live gate, and deterministic Phase 7 certification evidence.

The certification covers the complete CI gate, immutable container delivery, secret hygiene, HTTPS and host policy, authenticated operational data, security headers, portfolio schema validation, provider normalization, worker idempotency, dashboard state integrity, and staging/go-live controls.

Run `python scripts/certify_phase_7.py` after the full test suite. A successful report exits with code 0. The GitHub workflow repeats both gates before building a candidate image and retaining the report as deployment evidence.

External hosting, domain, TLS termination, managed PostgreSQL, secret-manager values, and production approval remain explicit operator choices. Certification proves that the release candidate is ready for those choices; it does not silently deploy infrastructure.
