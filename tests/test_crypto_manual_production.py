from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from foundation.integrations.crypto.manual_production import (
    REQUIRED_FILES,
    promote_package,
    validate_delivery,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_delivery(root: Path) -> Path:
    delivery = root / "run-001"
    delivery.mkdir(parents=True)
    for name in REQUIRED_FILES:
        path = delivery / name
        if name.endswith(".csv"):
            path.write_text("id,value\nA,1\n", encoding="utf-8")
        elif name == "package_summary.json":
            path.write_text(
                json.dumps(
                    {
                        "status": "PASS",
                        "platform_id": "crypto",
                        "package_id": "crypto-test-package",
                    }
                ),
                encoding="utf-8",
            )
        else:
            path.write_text("{}", encoding="utf-8")

    manifest = {
        "status": "PASS",
        "delivery_contract": "uip-crypto-delivery-v1",
        "run_id": "run-001",
        "files": [
            {
                "name": name,
                "size_bytes": (delivery / name).stat().st_size,
                "sha256": _sha256(delivery / name),
            }
            for name in sorted(REQUIRED_FILES)
        ],
    }
    manifest_path = delivery / "uip_delivery_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    latest = root / "latest.json"
    latest.write_text(
        json.dumps(
            {
                "run_id": "run-001",
                "delivery_directory": str(delivery),
                "manifest": str(manifest_path),
            }
        ),
        encoding="utf-8",
    )
    return latest


def test_valid_crypto_delivery_can_be_promoted(tmp_path: Path) -> None:
    latest = _build_delivery(tmp_path / "delivery")
    manifest, source = validate_delivery(latest)
    assert manifest["status"] == "PASS"

    destination = promote_package(source, tmp_path / "uip" / "latest")
    assert (destination / "package_summary.json").is_file()
    assert (destination / "export_manifest.csv").is_file()


def test_crypto_delivery_rejects_checksum_tampering(tmp_path: Path) -> None:
    latest = _build_delivery(tmp_path / "delivery")
    pointer = json.loads(latest.read_text(encoding="utf-8"))
    package = Path(pointer["delivery_directory"])
    (package / "asset_master.csv").write_text(
        "id,value\nTAMPERED,999\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="checksum mismatch"):
        validate_delivery(latest)
