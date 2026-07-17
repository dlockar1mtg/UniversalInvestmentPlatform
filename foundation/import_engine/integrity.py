"""File integrity validation for Universal Integration Packages."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv,hashlib
from foundation.import_engine.package import ManifestEntry,UniversalPackage,resolve_package_file
@dataclass(frozen=True)
class FileValidationResult:
    dataset_name:str; filename:str; required:bool; file_exists:bool; expected_row_count:int|None; actual_row_count:int; row_count_status:str; expected_sha256:str; calculated_sha256:str; checksum_status:str; validation_status:str; error_message:str
@dataclass(frozen=True)
class PackageValidationResult:
    package_id:str; platform_id:str; manifest_sha256:str; file_results:tuple[FileValidationResult,...]; warning_count:int; error_count:int
    @property
    def passed(self): return self.error_count==0
def calculate_sha256(path):
    d=hashlib.sha256()
    with path.open('rb') as h:
        for b in iter(lambda:h.read(1024*1024),b''): d.update(b)
    return d.hexdigest().lower()
def count_csv_rows(path):
    with path.open('r',encoding='utf-8-sig',newline='') as h:
        r=csv.reader(h)
        try: next(r)
        except StopIteration:return 0
        return sum(1 for row in r if any(str(v).strip() for v in row))
def _validate_entry(package,entry):
    source=resolve_package_file(package,entry)
    if not source.is_file():
        msg=(f"Required file is missing: {entry.filename}" if entry.required else f"Optional file is missing: {entry.filename}")
        return FileValidationResult(entry.dataset_name,entry.filename,entry.required,False,entry.expected_row_count,0,'NOT_CHECKED',entry.expected_sha256,'','NOT_CHECKED','FAILED' if entry.required else 'WARNING',msg)
    calc=calculate_sha256(source)
    checksum='PASS' if entry.expected_sha256 and calc==entry.expected_sha256.lower() else ('FAILED' if entry.expected_sha256 else 'NOT_DECLARED')
    actual=0; row_status='NOT_APPLICABLE'
    if source.suffix.lower()=='.csv':
        actual=count_csv_rows(source)
        row_status='NOT_DECLARED' if entry.expected_row_count is None else ('PASS' if actual==entry.expected_row_count else 'FAILED')
    errors=[]
    if checksum=='FAILED': errors.append(f"Checksum mismatch for {entry.filename}: expected {entry.expected_sha256}, calculated {calc}")
    if row_status=='FAILED': errors.append(f"Row-count mismatch for {entry.filename}: expected {entry.expected_row_count}, actual {actual}")
    status='PASS' if not errors else 'FAILED'
    return FileValidationResult(entry.dataset_name,entry.filename,entry.required,True,entry.expected_row_count,actual,row_status,entry.expected_sha256,calc,checksum,status,' | '.join(errors))
def validate_package_integrity(package):
    results=tuple(_validate_entry(package,e) for e in package.manifest_entries)
    warnings=sum(1 for r in results if r.validation_status=='WARNING')
    errors=sum(1 for r in results if r.validation_status=='FAILED')
    return PackageValidationResult(package.identity.package_id,package.identity.platform_id,calculate_sha256(package.manifest_path),results,warnings,errors)
