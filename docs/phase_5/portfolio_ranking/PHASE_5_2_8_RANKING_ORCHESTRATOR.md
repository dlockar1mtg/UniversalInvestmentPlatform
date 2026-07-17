# Phase 5.2.8 — Portfolio Ranking Orchestrator

The orchestrator provides the atomic batch boundary for portfolio ranking. It
validates normalized handoffs from comparability, portfolio context, factor, and
priority stages; resolves competition; generates explanations; preserves six
ordered intermediate artifacts per opportunity; and creates a deterministic
SHA-256 batch fingerprint. Input decisions and evidence remain immutable.
