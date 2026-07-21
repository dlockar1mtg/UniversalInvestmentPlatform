from __future__ import annotations

import pandas as pd
import pytest

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
