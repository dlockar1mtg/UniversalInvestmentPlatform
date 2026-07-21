"""Universal integration package discovery and manifest parsing."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv
import json
from foundation.import_engine.exceptions import ManifestError, PackageNotFoundError
MANIFEST_FILENAME="export_manifest.csv"
PLATFORM_STATUS_FILENAME="platform_status.csv"
def _first_value(row,candidates,default=""):
    normalized={str(k).strip().lower():str(v).strip() for k,v in row.items() if k is not None}
    for c in candidates:
        v=normalized.get(c.lower(),"")
        if v:return v
    return default
def _parse_bool(value,default=False):
    n=str(value).strip().lower()
    if n in {"true","1","yes","y","required"}: return True
    if n in {"false","0","no","n","optional"}: return False
    return default
def _parse_optional_int(value):
    c=str(value).strip().replace(",","")
    if not c:return None
    try:return int(float(c))
    except ValueError:return None
@dataclass(frozen=True)
class ManifestEntry:
    dataset_name:str
    filename:str
    expected_row_count:int|None
    expected_sha256:str
    required:bool
    validation_status:str
@dataclass(frozen=True)
class PackageIdentity:
    package_id:str
    platform_id:str
    run_id:str
    adapter_version:str
    contract_version:str
    generated_at_utc:str
@dataclass(frozen=True)
class UniversalPackage:
    package_path:Path
    manifest_path:Path
    platform_status_path:Path
    identity:PackageIdentity
    manifest_entries:tuple[ManifestEntry,...]
def _read_csv_rows(path):
    try:
        with path.open('r',encoding='utf-8-sig',newline='') as h:
            r=csv.DictReader(h)
            if not r.fieldnames: raise ManifestError(f"CSV has no header: {path}")
            return [{str(k).strip():'' if v is None else str(v).strip() for k,v in row.items() if k is not None} for row in r]
    except UnicodeDecodeError as exc: raise ManifestError(f"Unable to decode CSV as UTF-8: {path}") from exc
    except csv.Error as exc: raise ManifestError(f"Unable to parse CSV: {path}") from exc
def _resolve_safe_file(package_path,filename):
    if not filename: raise ManifestError('Manifest contains a blank filename.')
    root=package_path.resolve(); candidate=(root/filename).resolve()
    try:candidate.relative_to(root)
    except ValueError as exc: raise ManifestError(f"Manifest filename escapes package directory: {filename}") from exc
    return candidate
def _resolve_manifest_filename(package_path,declared_filename):
    if (package_path/declared_filename).is_file(): return declared_filename
    p=package_path/'supporting_native'/declared_filename
    if p.is_file(): return str(Path('supporting_native')/declared_filename)
    return declared_filename
def _parse_manifest(package_path,manifest_path):
    rows=_read_csv_rows(manifest_path); entries=[]
    for n,row in enumerate(rows,start=2):
        filename=_first_value(row,("relative_path","file_path","package_path","output_path","filename","file_name","output_filename"))
        if not filename: raise ManifestError(f"Manifest row {n} does not contain a filename.")
        filename=_resolve_manifest_filename(package_path,filename)
        dataset_name=_first_value(row,("dataset_name","dataset","contract_name","output_name","export_name","schema_name"),default=Path(filename).stem)
        expected_row_count=_parse_optional_int(_first_value(row,("row_count","records_published","record_count","expected_row_count","rows","rows_published","records","row_total")))
        expected_sha256=_first_value(row,("sha256","sha_256","checksum_sha256","file_sha256","checksum")).lower()
        required=_parse_bool(_first_value(row,("required","is_required","required_flag")),default=True)
        validation_status=_first_value(row,("validation_status","status","contract_status"))
        entries.append(ManifestEntry(dataset_name,filename,expected_row_count,expected_sha256,required,validation_status))
    if not entries: raise ManifestError(f"Manifest contains no dataset rows: {manifest_path}")
    return tuple(entries)
def _read_package_summary(package_path):
    summary_path=package_path/"package_summary.json"
    if not summary_path.is_file(): return {}
    try:
        payload=json.loads(summary_path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError,json.JSONDecodeError,OSError) as exc:
        raise ManifestError(
            f"Unable to parse package summary: {summary_path}"
        ) from exc
    if not isinstance(payload,dict):
        raise ManifestError(
            f"Package summary must contain a JSON object: {summary_path}"
        )
    return payload


def _summary_value(summary,candidates,default=""):
    normalized={
        str(key).strip().lower():value
        for key,value in summary.items()
    }
    for candidate in candidates:
        value=normalized.get(candidate.lower())
        if value is None: continue
        cleaned=str(value).strip()
        if cleaned: return cleaned
    return default


def _parse_identity(package_path,platform_status_path):
    rows=_read_csv_rows(platform_status_path)
    if not rows: raise ManifestError(f"Platform status contains no rows: {platform_status_path}")
    row=rows[0]
    summary=_read_package_summary(package_path)
    platform_id=_first_value(row,("platform_id","platform","source_platform"))
    run_id=_first_value(row,("run_id","platform_run_id","source_run_id"))
    adapter_version=_first_value(row,("adapter_version","integration_adapter_version"))
    if not adapter_version:
        adapter_version=_summary_value(
            summary,
            ("adapter_version","integration_adapter_version"),
        )
    contract_version=_first_value(row,("contract_version","schema_version"),default='v1')
    generated_at_utc=_first_value(row,("generated_at_utc","run_completed_at_utc","last_updated_at_utc"))
    package_id=_first_value(row,("package_id","export_package_id"),default=run_id or package_path.name)
    if not platform_id: raise ManifestError('Unable to establish platform_id from platform_status.csv.')
    if not package_id: raise ManifestError('Unable to establish package_id.')
    return PackageIdentity(package_id,platform_id,run_id,adapter_version,contract_version,generated_at_utc)
def discover_package(package_path):
    p=package_path.resolve()
    if not p.exists(): raise PackageNotFoundError(f"Package path does not exist: {p}")
    if not p.is_dir(): raise PackageNotFoundError(f"Package path is not a directory: {p}")
    manifest=p/MANIFEST_FILENAME; status=p/PLATFORM_STATUS_FILENAME
    if not manifest.is_file(): raise ManifestError(f"Export manifest not found: {manifest}")
    if not status.is_file(): raise ManifestError(f"Platform status file not found: {status}")
    entries=_parse_manifest(p,manifest)
    for e in entries:_resolve_safe_file(p,e.filename)
    identity=_parse_identity(p,status)
    return UniversalPackage(p,manifest,status,identity,entries)
def resolve_package_file(package,entry):
    return _resolve_safe_file(package.package_path,entry.filename)
