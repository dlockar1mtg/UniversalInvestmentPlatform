from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv


@dataclass(frozen=True)
class ContractField:
    name: str
    required: bool
    data_type: str = "string"


@dataclass(frozen=True)
class Contract:
    name: str
    fields: tuple[ContractField, ...]

    @property
    def columns(self) -> list[str]:
        return [field.name for field in self.fields]

    @property
    def required_columns(self) -> list[str]:
        return [field.name for field in self.fields if field.required]


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "required"}


def load_contract(schema_path: Path) -> Contract:
    """Load a Phase 0 CSV contract definition without assuming one exact header vocabulary."""
    if not schema_path.exists():
        raise FileNotFoundError(f"Universal contract definition not found: {schema_path}")
    with schema_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Universal contract definition is empty: {schema_path}")
    header = {key.lower(): key for key in rows[0]}
    name_key = next((header[k] for k in ("field_name", "column_name", "name", "field", "column") if k in header), None)
    if name_key is None:
        raise ValueError(f"Cannot locate field-name column in {schema_path}; headers={list(rows[0])}")
    required_key = next((header[k] for k in ("required", "is_required", "nullable", "null_allowed") if k in header), None)
    type_key = next((header[k] for k in ("data_type", "type", "dtype") if k in header), None)
    fields: list[ContractField] = []
    for row in rows:
        name = str(row.get(name_key, "")).strip()
        if not name:
            continue
        required = False
        if required_key:
            raw = row.get(required_key)
            if required_key.lower() in {"nullable", "null_allowed"}:
                required = not _truthy(raw)
            else:
                required = _truthy(raw)
        fields.append(ContractField(name=name, required=required, data_type=str(row.get(type_key, "string") if type_key else "string")))
    if not fields:
        raise ValueError(f"No contract fields were found in {schema_path}")
    return Contract(schema_path.stem.replace("_schema", ""), tuple(fields))
