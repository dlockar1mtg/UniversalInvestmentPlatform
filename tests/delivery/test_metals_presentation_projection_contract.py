from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_metals_tactical_presentation_extension_is_fail_closed() -> None:
    payload = json.loads(
        (ROOT / "config/presentation/dash_read_1_metals_tactical_extension.json").read_text(encoding="utf-8")
    )
    assert payload["extension_id"] == "DASH-READ-1-METALS-TACTICAL-EVIDENCE"
    assert payload["source_database_sha256"] == "dff98e56d27cbc5ef879c18939309c5ab8661fa8fa6dfe74e82537fd53954f7c"
    assert payload["controls"] == {
        "current_authority_only": True,
        "presentation_store_is_analytical_authority": False,
        "missing_authority_may_be_synthesized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "tactical_posture_authorized": False,
    }
    assert set(payload["surfaces"]) == {
        "metals_model_component",
        "metals_regime_probability",
        "metals_uncertainty_adjusted",
        "metals_recommendation_change",
        "metals_data_freshness",
        "metals_platform_health",
    }


def test_publication_model_projects_metals_tactical_evidence() -> None:
    source = (ROOT / "foundation/presentation/publication_model.py").read_text(encoding="utf-8")
    assert "build_metals_tactical_records" in source
    assert "records.extend(build_metals_tactical_records(repository_root, connection, source_sha256))" in source


def test_projection_does_not_create_tactical_posture_or_cross_domain_rank() -> None:
    source = (ROOT / "foundation/presentation/metals_tactical_projection.py").read_text(encoding="utf-8")
    assert '"tactical_posture_authorized": False' in source
    assert '"cross_domain_rank_authorized": False' in source
    assert "ACCUMULATE" not in source
    assert "REDUCE" not in source


def test_projection_verifier_bootstraps_repository_import_path() -> None:
    source = (ROOT / "scripts/verify_metals_presentation_projection.py").read_text(encoding="utf-8")
    assert "import sys" in source
    assert "ROOT = Path(__file__).resolve().parents[1]" in source
    assert "sys.path.insert(0, str(ROOT))" in source
    assert "from foundation.presentation.publication_model import build_presentation_publication" in source
