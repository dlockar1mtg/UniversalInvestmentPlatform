from __future__ import annotations

from pathlib import Path
import shutil
import sys


def main() -> int:
    bundle=Path(__file__).resolve().parents[1]
    target=Path.cwd().resolve()
    expected=["schemas","exchange","scripts","data"]
    missing=[name for name in expected if not (target/name).exists()]
    if missing:
        print(f"Run this installer from the Universal repository root. Missing: {missing}",file=sys.stderr); return 1
    copies=[
        (bundle/"exchange"/"metals"/"adapter",target/"exchange"/"metals"/"adapter"),
        (bundle/"exchange"/"metals"/"config",target/"exchange"/"metals"/"config"),
    ]
    for src,dst in copies:
        dst.mkdir(parents=True,exist_ok=True)
        for item in src.iterdir():
            if item.is_file(): shutil.copy2(item,dst/item.name)
    for filename in ["run_metals_universal_export.py"]:
        shutil.copy2(bundle/"scripts"/filename,target/"scripts"/filename)
    docs_target=target/"exchange"/"metals"/"docs"; docs_target.mkdir(parents=True,exist_ok=True)
    for filename in ["PHASE_1_2_RUNBOOK.md","PHASE_1_2_ARCHITECTURE.md"]:
        shutil.copy2(bundle/"docs"/filename,docs_target/filename)
    print("Phase 1.2 Metals Universal Export Adapter installed.")
    print("Next: python scripts\\run_metals_universal_export.py --metals-root C:\\Users\\DevonLockard\\metals")
    return 0

if __name__=="__main__": raise SystemExit(main())
