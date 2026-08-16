from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWER = ROOT / "scripts" / "review_r3_crypto_output_rationality.py"

OLD = '''    require(status_row.get("run_status", "").strip().upper() == "PASS", "Crypto platform_status run_status is PASS", checks)'''
NEW = '''    require(status_row.get("run_status", "").strip().lower() == "success", "Crypto platform_status run_status is native success", checks)'''


def main() -> int:
    if not REVIEWER.is_file():
        raise RuntimeError(f"Missing Crypto R3 reviewer: {REVIEWER}")

    text = REVIEWER.read_text(encoding="utf-8")

    if OLD not in text:
        if NEW in text:
            print("UIP_R3_CRYPTO_PLATFORM_STATUS_SEMANTIC_CORRECTION=ALREADY_APPLIED")
            return 0
        raise RuntimeError(
            "Expected pre-correction platform-status assertion was not found; refusing blind edit."
        )

    text = text.replace(OLD, NEW, 1)
    with REVIEWER.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)

    print("UIP_R3_CRYPTO_PLATFORM_STATUS_SEMANTIC_CORRECTION=PASS")
    print("NATIVE_PLATFORM_STATUS_SUCCESS_VALUE=success")
    print("PRODUCER_ERROR_COUNT_REQUIREMENT=0")
    print(f"UPDATED_FILE={REVIEWER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
