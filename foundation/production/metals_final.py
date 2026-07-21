"""Final Phase 8 certification gates for Metals integration and retirement."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from exchange.metals.adapter import build_package

from .metals_readiness import evaluate_metals_readiness


REQUIRED_CERTIFICATIONS = (
    "PHASE_8_1_1_SOURCE_HEALTH_BASELINE.md",
    "PHASE_8_1_3_CAPABILITY_DECISIONS.md",
    "PHASE_8_1_4_EXPORT_COMPATIBILITY_CERTIFICATION.md",
    "PHASE_8_2_PROVIDER_HARDENING_CERTIFICATION.md",
    "PHASE_8_3_REGISTRY_CERTIFICATION.md",
    "PHASE_8_4_VEHICLE_CONSTRAINT_CERTIFICATION.md",
    "PHASE_8_5_PERSISTENCE_INDEPENDENCE_CERTIFICATION.md",
    "PHASE_8_6_MODEL_PARITY_CERTIFICATION.md",
    "PHASE_8_7_PRODUCTION_READINESS_CERTIFICATION.md",
)


def scan_runtime_isolation(universal_root: str | Path) -> dict:
    root = Path(universal_root)
    forbidden = "metals_" + "platform"
    violations = []
    for relative_root in (Path("foundation"), Path("exchange/metals/adapter")):
        for path in sorted((root / relative_root).rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), start=1):
                stripped = line.strip()
                if forbidden in stripped and (
                    stripped.startswith("import ") or stripped.startswith("from ")
                ):
                    violations.append(
                        {"path": path.relative_to(root).as_posix(), "line": line_number}
                    )
    adapter_text = (root / "exchange" / "metals" / "adapter" / "adapter.py").read_text(
        encoding="utf-8"
    )
    if "import duckdb" in adapter_text or "duckdb.connect" in adapter_text:
        violations.append({"path": "exchange/metals/adapter/adapter.py", "line": 0})
    fallback = inspect.signature(build_package).parameters[
        "allow_legacy_database_fallback"
    ].default
    if fallback is not False:
        violations.append({"path": "exchange/metals/adapter/adapter.py", "line": 0})
    return {
        "status": "PASS" if not violations else "FAILED",
        "violations": violations,
        "legacy_database_fallback_default": fallback,
    }


def certify_phase_8_metals(
    universal_root: str | Path,
    metals_root: str | Path,
    package_root: str | Path,
    *,
    include_live_providers: bool = True,
) -> dict:
    universal = Path(universal_root)
    package = Path(package_root)
    components = []

    def record(name, operation):
        try:
            detail = operation()
            components.append({"name": name, "status": "PASS", "detail": detail})
        except Exception as exc:
            components.append(
                {
                    "name": name,
                    "status": "FAILED",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    readiness = evaluate_metals_readiness(
        metals_root,
        package,
        universal_root=universal,
        include_live_providers=include_live_providers,
    )
    if readiness["ready"]:
        components.append(
            {
                "name": "production_readiness",
                "status": "PASS",
                "detail": {
                    "components": readiness["component_count"],
                    "failed_components": readiness["failed_components"],
                },
            }
        )
    else:
        components.append(
            {
                "name": "production_readiness",
                "status": "FAILED",
                "detail": readiness,
            }
        )

    def certification_documents():
        root = universal / "docs" / "phase_8" / "metals"
        missing = [name for name in REQUIRED_CERTIFICATIONS if not (root / name).is_file()]
        if missing:
            raise RuntimeError(f"missing Phase 8 certifications: {missing}")
        return {"documents": len(REQUIRED_CERTIFICATIONS)}

    def release_provenance():
        version = (universal / "exchange" / "metals" / "adapter" / "VERSION").read_text(
            encoding="utf-8"
        ).strip()
        config = json.loads(
            (universal / "exchange" / "metals" / "config" / "adapter_config.json").read_text(
                encoding="utf-8"
            )
        )
        summary = json.loads((package / "package_summary.json").read_text(encoding="utf-8"))
        versions = {version, config.get("adapter_version"), summary.get("adapter_version")}
        if versions != {"2.0.0"}:
            raise RuntimeError(f"adapter release provenance mismatch: {sorted(map(str, versions))}")
        return {"adapter_version": version, "package_id": summary.get("package_id")}

    def isolation():
        result = scan_runtime_isolation(universal)
        if result["status"] != "PASS":
            raise RuntimeError(f"runtime isolation violations: {result['violations']}")
        return result

    def retirement():
        path = universal / "docs" / "phase_8" / "metals" / "METALS_LEGACY_RETIREMENT_RUNBOOK.md"
        if not path.is_file():
            raise RuntimeError("legacy retirement runbook is missing")
        return {"runbook": path.relative_to(universal).as_posix()}

    record("prior_certifications", certification_documents)
    record("release_provenance", release_provenance)
    record("runtime_isolation", isolation)
    record("legacy_retirement", retirement)

    failed = [item["name"] for item in components if item["status"] != "PASS"]
    return {
        "status": "PASS" if not failed else "FAILED",
        "certified": not failed,
        "phase": "8.8",
        "failed_components": failed,
        "components": components,
    }
