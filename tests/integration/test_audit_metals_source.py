from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "audit_metals_source.py"
SPEC = importlib.util.spec_from_file_location("audit_metals_source", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write(root: Path, relative: str, content: str = "x") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_inventory_classifies_domain_and_superseded_components(tmp_path: Path) -> None:
    _write(tmp_path, "metals_platform/collectors/fred.py")
    _write(tmp_path, "metals_platform/vehicles/selection.py")
    _write(tmp_path, "metals_platform/forecasting/engine.py")
    _write(tmp_path, "metals_platform/database/schema.py")
    _write(tmp_path, "metals_platform/analytics/engine_before_v5.py")
    _write(tmp_path, "tests/test_vehicle_selection.py")
    _write(tmp_path, "data/generated.csv")

    records = MODULE.build_inventory(tmp_path)
    by_path = {record.relative_path: record for record in records}

    assert "data/generated.csv" not in by_path
    assert by_path["metals_platform/collectors/fred.py"].initial_classification == "adapt"
    assert by_path["metals_platform/vehicles/selection.py"].initial_classification == "adapt"
    assert by_path["metals_platform/forecasting/engine.py"].initial_classification == "replace"
    assert by_path["metals_platform/database/schema.py"].initial_classification == "replace"
    assert by_path["metals_platform/analytics/engine_before_v5.py"].initial_classification == "archive"
    assert by_path["tests/test_vehicle_selection.py"].initial_classification == "evaluate"


def test_inventory_outputs_csv_json_and_summary(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    _write(source, "metals_platform/collectors/fred.py", "print('ok')")
    _write(source, "tests/test_fred.py")

    records = MODULE.build_inventory(source)
    MODULE.write_inventory(records, output)

    assert (output / "metals_component_inventory.csv").is_file()
    assert (output / "metals_component_inventory.json").is_file()
    summary = (output / "metals_component_inventory_summary.json").read_text(
        encoding="utf-8"
    )
    assert '"file_count": 2' in summary
    assert '"test_file_count": 1' in summary
