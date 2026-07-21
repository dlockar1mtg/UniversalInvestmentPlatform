from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "audit_crypto_source.py"
SPEC = importlib.util.spec_from_file_location("audit_crypto_source", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write(root: Path, relative: str, content: str = "x") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_inventory_excludes_secrets_and_generated_data(tmp_path: Path) -> None:
    _write(tmp_path, "crypto_platform/provider.py")
    _write(tmp_path, "crypto_platform/ml/model.py")
    _write(tmp_path, "crypto_platform/optimization/engine.py")
    _write(tmp_path, "config/assets.yaml")
    _write(tmp_path, "test_v13_schema.py")
    _write(tmp_path, "upgrade_to_v12.py")
    _write(tmp_path, ".env", "SECRET=value")
    _write(tmp_path, ".env.example", "SECRET=")
    _write(tmp_path, "data/crypto_intelligence.duckdb")

    records = MODULE.build_inventory(tmp_path)
    by_path = {record.relative_path: record for record in records}

    assert ".env" not in by_path
    assert ".env.example" not in by_path
    assert "data/crypto_intelligence.duckdb" not in by_path
    assert by_path["crypto_platform/ml/model.py"].initial_classification == "replace"
    assert (
        by_path["crypto_platform/optimization/engine.py"].initial_classification
        == "replace"
    )
    assert by_path["config/assets.yaml"].initial_classification == "adapt"
    assert by_path["test_v13_schema.py"].initial_classification == "evaluate"
    assert by_path["upgrade_to_v12.py"].initial_classification == "archive"


def test_inventory_outputs_csv_json_and_summary(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    _write(source, "crypto_platform/provider.py", "print('ok')")
    _write(source, "test_v13_schema.py")

    records = MODULE.build_inventory(source)
    MODULE.write_inventory(records, output)

    assert (output / "crypto_component_inventory.csv").is_file()
    assert (output / "crypto_component_inventory.json").is_file()
    summary = (output / "crypto_component_inventory_summary.json").read_text(
        encoding="utf-8"
    )
    assert '"file_count": 2' in summary
    assert '"test_file_count": 1' in summary
