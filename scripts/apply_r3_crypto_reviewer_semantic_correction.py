from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWER = ROOT / "scripts" / "review_r3_crypto_output_rationality.py"

OLD_MAP = 'ALLOWED_NATIVE_TO_UNIVERSAL = {"WAIT": "watch", "AVOID": "sell"}'
NEW_MAP = '''ALLOWED_NATIVE_TO_UNIVERSAL = {
    "BUY": "buy",
    "ACCUMULATE": "accumulate",
    "HOLD": "hold",
    "WAIT": "watch",
    "REDUCE": "reduce",
    "SELL": "sell",
    "AVOID": "sell",
}'''
OLD_CHECK = 'checks.append("Certified Crypto native recommendation mapping WAIT->watch and AVOID->sell is preserved")'
NEW_CHECK = 'checks.append("Certified Crypto native recommendation vocabulary and deterministic universal normalization are preserved")'
OLD_KEY = '"wait_to_watch_preserved": all(item["universal"] == ALLOWED_NATIVE_TO_UNIVERSAL[item["native"]] for item in mapping_evidence),'
NEW_KEY = '"certified_native_recommendation_mapping_preserved": all(item["universal"] == ALLOWED_NATIVE_TO_UNIVERSAL[item["native"]] for item in mapping_evidence),'


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} occurrence, found {count}.")
    return text.replace(old, new, 1)


def main() -> int:
    if not REVIEWER.is_file():
        raise RuntimeError(f"Missing reviewer: {REVIEWER}")

    text = REVIEWER.read_text(encoding="utf-8")
    text = replace_exact(text, OLD_MAP, NEW_MAP, "recommendation map")
    text = replace_exact(text, OLD_CHECK, NEW_CHECK, "mapping check text")
    text = replace_exact(text, OLD_KEY, NEW_KEY, "semantic evidence key")

    with REVIEWER.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)

    print("UIP_R3_CRYPTO_REVIEWER_SEMANTIC_CORRECTION=PASS")
    print("AUTHORIZED_NATIVE_LABELS=BUY,ACCUMULATE,HOLD,WAIT,REDUCE,SELL,AVOID")
    print("WAIT_NORMALIZES_TO=watch")
    print("AVOID_NORMALIZES_TO=sell")
    print("UNKNOWN_NATIVE_LABELS_FAIL_CLOSED=TRUE")
    print(f"UPDATED_FILE={REVIEWER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
