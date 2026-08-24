from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_metals_promotable_native_evidence.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_metals_promotable_native_evidence", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_audit_package_requires_complete_supporting_native_evidence(tmp_path: Path):
    module = _load_module()
    package = tmp_path / "metals-package"
    support = package / "supporting_native"
    support.mkdir(parents=True)

    (support / "latest_forecast_model_components.csv").write_text(
        "forecast_run_id,metal,horizon_months,model_name,model_forecast,model_weight\n"
        "r1,gold,3,m1,0.1,0.5\n",
        encoding="utf-8",
    )
    (support / "latest_learned_regime_probabilities.csv").write_text(
        "forecast_run_id,metal,regime,probability\n"
        "r1,gold,expansion,1.0\n",
        encoding="utf-8",
    )
    (support / "latest_uncertainty_adjusted_views.csv").write_text(
        "forecast_run_id,ticker,metal,horizon_months,raw_expected_return,uncertainty_penalty,downside_penalty,adjusted_expected_return\n"
        "r1,GLD,gold,3,0.1,0.01,0.02,0.07\n",
        encoding="utf-8",
    )
    for filename in (
        "latest_recommendation_change_explanations.csv",
        "latest_data_freshness_details.csv",
        "latest_platform_health_score.csv",
    ):
        (support / filename).write_text("key,value\na,b\n", encoding="utf-8")

    result = module.audit_package(package)
    assert result["complete"] is True
    assert result["files"]["latest_forecast_model_components.csv"]["rows"] == 1

    (support / "latest_learned_regime_probabilities.csv").unlink()
    blocked = module.audit_package(package)
    assert blocked["complete"] is False
    assert blocked["files"]["latest_learned_regime_probabilities.csv"]["present"] is False
