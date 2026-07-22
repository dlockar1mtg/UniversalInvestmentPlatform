"""Verify the deployed eBay compliance challenge endpoint without exposing secrets."""

from __future__ import annotations

import argparse
import hashlib
import os
import secrets
import sys

import requests


DEFAULT_ENDPOINT = (
    "https://uiip-free-staging.onrender.com/"
    "api/compliance/ebay/account-deletion"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=os.getenv("EBAY_DELETION_ENDPOINT_URL", DEFAULT_ENDPOINT))
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    token = os.getenv("EBAY_DELETION_VERIFICATION_TOKEN", "").strip()
    if not token:
        print("EBAY COMPLIANCE ENDPOINT: FAIL")
        print("Reason: EBAY_DELETION_VERIFICATION_TOKEN is not set locally.")
        return 2

    challenge = secrets.token_urlsafe(24)
    expected = hashlib.sha256(
        f"{challenge}{token}{args.endpoint}".encode("utf-8")
    ).hexdigest()

    try:
        response = requests.get(
            args.endpoint,
            params={"challenge_code": challenge},
            timeout=args.timeout,
        )
        response.raise_for_status()
        actual = response.json().get("challengeResponse")
    except (requests.RequestException, ValueError) as exc:
        print("EBAY COMPLIANCE ENDPOINT: FAIL")
        print(f"Reason: {exc}")
        return 1

    if actual != expected:
        print("EBAY COMPLIANCE ENDPOINT: FAIL")
        print("Reason: challenge response did not match the local expectation.")
        return 1

    print("EBAY COMPLIANCE ENDPOINT: PASS")
    print(f"Endpoint: {args.endpoint}")
    print("Verification token printed: NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
