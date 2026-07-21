from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from exchange.metals.adapter import adapter as adapter_module
from exchange.metals.adapter.config import load_config
from exchange.metals.adapter.contracts import Contract, ContractField
from exchange.metals.adapter.parity import MetalsParityError, validate_model_evidence


def evidence():
    forecasts = pd.DataFrame([
        {
            "forecast_run_id": 7,
            "metal": "gold",
            "horizon_months": 3,
            "expected_return": 0.08,
        }
    ])
    components = pd.DataFrame([
        {
            "forecast_run_id": 7,
            "metal": "gold",
            "horizon_months": 3,
            "model_name": "trend",
            "model_forecast": 0.10,
            "model_weight": 0.6,
        },
        {
            "forecast_run_id": 7,
            "metal": "gold",
            "horizon_months": 3,
            "model_name": "macro",
            "model_forecast": 0.05,
            "model_weight": 0.4,
        },
    ])
    regimes = pd.DataFrame([
        {"forecast_run_id": 7, "metal": "gold", "regime": "bull", "probability": 0.7},
        {"forecast_run_id": 7, "metal": "gold", "regime": "bear", "probability": 0.3},
    ])
    adjusted = pd.DataFrame([
        {
            "forecast_run_id": 7,
            "ticker": "GLD",
            "metal": "gold",
            "horizon_months": 3,
            "raw_expected_return": 0.10,
            "uncertainty_penalty": 0.02,
            "downside_penalty": 0.01,
            "adjusted_expected_return": 0.07,
        }
    ])
    return forecasts, components, regimes, adjusted


def test_model_evidence_reconciles() -> None:
    checks = validate_model_evidence(*evidence())
    assert [check.name for check in checks] == [
        "forecast_keys",
        "model_components",
        "regime_probabilities",
        "uncertainty_adjustments",
    ]


def test_model_evidence_rejects_weight_drift() -> None:
    forecasts, components, regimes, adjusted = evidence()
    components.loc[0, "model_weight"] = 0.5
    with pytest.raises(MetalsParityError, match="weights do not sum"):
        validate_model_evidence(forecasts, components, regimes, adjusted)


def test_model_evidence_rejects_invalid_regime_probabilities() -> None:
    forecasts, components, regimes, adjusted = evidence()
    regimes.loc[0, "probability"] = 1.1
    with pytest.raises(MetalsParityError, match="between zero and one"):
        validate_model_evidence(forecasts, components, regimes, adjusted)


def test_model_evidence_rejects_uncertainty_arithmetic_drift() -> None:
    forecasts, components, regimes, adjusted = evidence()
    adjusted.loc[0, "adjusted_expected_return"] = 0.08
    with pytest.raises(MetalsParityError, match="does not reconcile"):
        validate_model_evidence(forecasts, components, regimes, adjusted)


def test_model_evidence_rejects_orphan_component_keys() -> None:
    forecasts, components, regimes, adjusted = evidence()
    components.loc[0, "horizon_months"] = 12
    with pytest.raises(MetalsParityError, match="coverage"):
        validate_model_evidence(forecasts, components, regimes, adjusted)


def test_native_forecast_maps_to_universal_contract_fields(tmp_path: Path) -> None:
    exports = tmp_path / "exports"
    exports.mkdir()
    pd.DataFrame([
        {
            "forecast_run_id": 7,
            "metal": "gold",
            "horizon_months": 12,
            "expected_return": 0.08,
            "lower_bound": -0.05,
            "upper_bound": 0.20,
            "forecast_volatility": 0.15,
            "downside_probability": 0.25,
            "dominant_regime": "neutral",
            "model_agreement": 82,
        }
    ]).to_csv(exports / "latest_metal_forecasts.csv", index=False)
    context = adapter_module.BuildContext(
        Path.cwd(),
        tmp_path,
        tmp_path / "output",
        tmp_path / "schemas",
        load_config(Path("exchange/metals/config/adapter_config.json")),
        "package-1",
        "2026-07-21T12:00:00+00:00",
    )
    contract = Contract(
        "forecasts",
        (
            ContractField("universal_asset_id", True),
            ContractField("forecast_horizon_months", True),
            ContractField("expected_total_return", False),
            ContractField("probability_positive_return", False),
            ContractField("forecast_confidence", False),
            ContractField("model_version", False),
        ),
    )
    result = adapter_module._forecasts(context, contract, exports)
    row = result.iloc[0]
    assert row["universal_asset_id"] == "metals:commodity:gold"
    assert row["forecast_horizon_months"] == 12
    assert row["expected_total_return"] == pytest.approx(0.08)
    assert row["probability_positive_return"] == pytest.approx(0.75)
    assert row["forecast_confidence"] == pytest.approx(82)
    assert row["model_version"] == "metals-v8.1"
