from pathlib import Path

from foundation.presentation.metals_identity_bridge import (
    COMMODITY_RICH_FAMILIES,
    canonical_presentation_asset_id,
)


ROOT = Path(__file__).resolve().parents[2]
PROJECTION = ROOT / "foundation" / "presentation" / "metals_rich_projection.py"
DESIGN = ROOT / "docs" / "project_control" / "metals_commodity_vehicle_implementation_design_v1.md"


def test_identity_bridge_normalizes_only_governed_commodity_rich_families():
    assert COMMODITY_RICH_FAMILIES == {
        "model_component",
        "recommendation_change",
        "regime_probability",
        "uncertainty_adjusted",
        "tactical_state",
    }
    assert canonical_presentation_asset_id(
        "tactical_state", "metals:commodity:metals:commodity:gold"
    ) == "metals:commodity:gold"
    assert canonical_presentation_asset_id(
        "regime_probability", "metals:commodity:metals:commodity:silver"
    ) == "metals:commodity:silver"
    assert canonical_presentation_asset_id(
        "model_component", "METALS:COMMODITY:COPPER"
    ) == "metals:commodity:copper"
    assert canonical_presentation_asset_id(
        "risk", "metals:vehicle:GLD"
    ) == "metals:vehicle:GLD"


def test_projection_preserves_source_identity_provenance():
    text = PROJECTION.read_text(encoding="utf-8")
    assert "canonical_presentation_asset_id" in text
    assert 'payload["_rich_source_asset_id"] = source_asset_id' in text
    assert 'payload["_presentation_asset_id"] = asset_id' in text


def test_vehicle_design_restores_registered_purchase_options_without_fake_ranking():
    text = DESIGN.read_text(encoding="utf-8")
    for ticker in ("GLD", "IAU", "SGOL", "SLV", "SIVR", "PPLT", "CPER", "COPX", "URA", "URNM"):
        assert ticker in text
    assert "Preferred-vehicle ranking is NOT YET AUTHORIZED" in text
    assert "representative test scores are not certified live investment authority" in text
    assert "using vehicle Risk V1 as commodity risk" in text
    assert "automatic execution" in text
