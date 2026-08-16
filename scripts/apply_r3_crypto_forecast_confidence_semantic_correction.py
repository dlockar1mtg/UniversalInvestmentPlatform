from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWER = ROOT / "scripts" / "review_r3_crypto_output_rationality.py"

OLD = '''        confidence = parse_float(row.get("forecast_confidence", ""), field="forecast_confidence", asset=asset)\n        if confidence is not None and not (0.0 <= confidence <= 1.0):\n            raise RuntimeError(f"Crypto forecast_confidence outside probability-style bounds for {asset}: {confidence}")\n'''

NEW = '''        confidence = parse_float(row.get("forecast_confidence", ""), field="forecast_confidence", asset=asset)\n        if confidence is not None and not (0.0 <= confidence <= 100.0):\n            raise RuntimeError(f"Crypto forecast_confidence outside certified 0-to-100 score bounds for {asset}: {confidence}")\n'''

OLD_CHECK = 'Crypto forecast numeric fields are finite and probability/confidence fields remain within mathematical bounds when populated'
NEW_CHECK = 'Crypto forecast numeric fields are finite; probability_positive_return remains within 0-to-1 bounds and forecast_confidence remains within certified 0-to-100 score bounds when populated'


def main() -> int:
    if not REVIEWER.is_file():
        raise RuntimeError(f"Missing reviewer: {REVIEWER}")

    text = REVIEWER.read_text(encoding="utf-8")
    if NEW in text and NEW_CHECK in text:
        print("UIP_R3_CRYPTO_FORECAST_CONFIDENCE_SEMANTIC_CORRECTION=PASS")
        print("FORECAST_CONFIDENCE_BOUNDS=0_TO_100")
        print("PROBABILITY_POSITIVE_RETURN_BOUNDS=0_TO_1")
        print(f"UPDATED_FILE={REVIEWER}")
        return 0

    if OLD not in text:
        raise RuntimeError("Expected pre-correction forecast-confidence assertion was not found; refusing ambiguous edit.")
    if OLD_CHECK not in text:
        raise RuntimeError("Expected pre-correction forecast check description was not found; refusing ambiguous edit.")

    text = text.replace(OLD, NEW, 1).replace(OLD_CHECK, NEW_CHECK, 1)
    with REVIEWER.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)

    verify = REVIEWER.read_text(encoding="utf-8")
    if NEW not in verify or NEW_CHECK not in verify or OLD in verify:
        raise RuntimeError("Crypto R3 forecast-confidence semantic correction did not verify.")

    print("UIP_R3_CRYPTO_FORECAST_CONFIDENCE_SEMANTIC_CORRECTION=PASS")
    print("FORECAST_CONFIDENCE_BOUNDS=0_TO_100")
    print("PROBABILITY_POSITIVE_RETURN_BOUNDS=0_TO_1")
    print(f"UPDATED_FILE={REVIEWER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
