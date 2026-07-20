# Phase 7.7.2 - Authenticated Hosted Portfolio Ingestion

This increment adds operator-only, bounded CSV ingestion and viewer-only snapshot retrieval.

## Security boundary

- Uploads require HTTPS in hosted staging and an `operator` API credential.
- CSV bodies are limited to 256 KiB and must be UTF-8 `text/csv`.
- The complete file validates before a transaction begins.
- Raw CSV bytes and local filenames are never persisted or logged.
- Audit evidence contains only redacted credentials, snapshot identity, fingerprint, and cardinality.
- Repeated identical uploads return the existing content-addressed snapshot.
- Current positions require viewer authorization; history returns summaries only.

The local upload CLI reads the excluded holdings file, validates it locally, and sends it directly to the hosted HTTPS endpoint.
