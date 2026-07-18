# Phase 5.3.2 — Capital Supply and Reserve Engine

This engine reconciles gross capital into unavailable, reserved, and deployable
amounts before opportunity sizing begins. Contractual pool reserves are applied
first, followed by required policy reserves and strategic dry powder. Rules are
deterministically ordered and preserve requested, applied, capped, and unmet
reserve amounts.

The engine never allows negative deployable capital and enforces:
`gross = unavailable + reserved + deployable`.
