import json

from foundation.intelligence.scoring import (
    ExplanationEngine,
    explanation_to_dict,
    explanation_to_json,
)

from .test_explanation_engine import build_composite


def test_explanation_to_dict_is_json_safe() -> None:
    explanation = ExplanationEngine().explain(build_composite())
    payload = explanation_to_dict(explanation)
    assert payload["asset_id"] == "crypto:bitcoin"
    json.dumps(payload)


def test_explanation_to_json_is_stable() -> None:
    explanation = ExplanationEngine().explain(build_composite())
    first = explanation_to_json(explanation)
    second = explanation_to_json(explanation)
    assert first == second
    assert '"score_band"' in first
