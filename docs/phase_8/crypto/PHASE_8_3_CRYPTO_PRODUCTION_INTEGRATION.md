# Phase 8.3 — Crypto Production Integration

This milestone makes UIP the owner of the complete manual Crypto production transaction while preserving the standalone Crypto repository as the owner of source collection, model execution, governance, and universal export.

## Production sequence

1. Run the standalone governed Crypto production pipeline.
2. Require a PASS production summary and PASS universal export.
3. Prepare the standalone `uip-crypto-delivery-v1` delivery.
4. Validate the delivery pointer, contract, required files, and SHA-256 checksums.
5. Promote the certified package atomically to `data/integration/crypto/latest`.
6. Run UIP package discovery and integrity validation.
7. Import through the transactional Universal Import Engine.
8. Synchronize the audit registry.
9. Only after successful import, publish UIP-controlled Crypto intelligence and dashboard datasets.
10. Preserve `last_successful_cycle.json` and reconcile duplicate package runs safely.

## Manual command

```powershell
cd C:\Users\DevonLockard\InvestmentPlatform

python scripts\run_crypto_manual_production_cycle.py `
    --crypto-root "C:\Users\DevonLockard\crypto"
```

The standalone repository may instead be located at another path, including `C:\Users\DevonLockard\CryptoIntelligencePlatform`; provide the actual local repository root.

## Reconciliation command

Use the existing latest production run and delivery without rerunning the standalone pipeline:

```powershell
python scripts\run_crypto_manual_production_cycle.py `
    --crypto-root "C:\Users\DevonLockard\crypto" `
    --skip-source-run
```

## UIP-controlled outputs

- `data/integration/crypto/latest/`
- `data/operations/uip_crypto/latest/crypto_dashboard.csv`
- `data/operations/uip_crypto/latest/crypto_intelligence.csv`
- `data/operations/uip_crypto/latest/publication_status.json`
- `data/operations/uip_crypto/last_successful_cycle.json`
