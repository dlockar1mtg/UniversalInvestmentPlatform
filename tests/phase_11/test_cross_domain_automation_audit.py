from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_cross_domain_automation.py"
CONTRACT = ROOT / "config" / "phase_11" / "cross_domain_automation_contract.json"

def load_module():
    import sys

    spec = importlib.util.spec_from_file_location("audit_cross_domain_automation", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def test_contract_lists_all_domains():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert set(payload["domains"]) == {"metals", "crypto", "mtg"}

def test_all_configured_repositories_exist():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    for config in payload["domains"].values():
        assert Path(config["repository_path"]).is_dir()

def test_audit_detects_configured_workflows():
    module = load_module()
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    for domain, config in payload["domains"].items():
        findings = module.audit_domain(domain, config)
        workflow_findings = [f for f in findings if f.category == "workflow"]
        assert workflow_findings
        assert all(f.status == "PASS" for f in workflow_findings)
