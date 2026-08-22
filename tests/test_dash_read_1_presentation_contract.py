from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.presentation.read_model_contracts import (
    CONTRACT_PATH,
    PresentationContractError,
    load_presentation_contract,
    validate_authority_schema,
)


ROOT = Path(__file__).resolve().parents[1]


def _temp_config(tmp_path: Path) -> ImportEngineConfig:
    base = ImportEngineConfig.from_repository_root(ROOT)
    return ImportEngineConfig(
        repository_root=ROOT,
        database_path=tmp_path / "dash_read_1.duckdb",
        schema_root=base.schema_root,
        integration_root=base.integration_root,
        validation_root=tmp_path / "validation",
    )


def test_dash_read_1_contract_preserves_certified_domain_boundaries() -> None:
    contract = load_presentation_contract(ROOT)
    assert contract.contract_version == "1.0.0"
    assert contract.milestone == "DASH_READ_1_CERTIFIED_PRESENTATION_READ_MODEL_PUBLICATION_CONTRACT"
    assert tuple(domain.domain_id for domain in contract.domains) == ("crypto", "metals", "mtg")
    by_domain = {domain.domain_id: domain for domain in contract.domains}

    assert by_domain["crypto"].authority_mode == "GENERIC_CURRENT_VIEWS"
    assert by_domain["metals"].authority_mode == "GENERIC_CURRENT_VIEWS"
    assert by_domain["crypto"].native_rank_available is False
    assert by_domain["metals"].native_rank_available is False
    assert by_domain["crypto"].current_price_contract == "NOT_BOUND_IN_DASH_READ_1_GENERIC_SURFACE"
    assert by_domain["metals"].current_price_contract == "NOT_BOUND_IN_DASH_READ_1_GENERIC_SURFACE"

    mtg = by_domain["mtg"]
    assert mtg.authority_mode == "MTG_NATIVE_CURRENT_ONLY"
    assert mtg.native_rank_available is True
    assert mtg.current_price_contract == "NATIVE_CURRENT_PRICE_WHEN_AUTHORITY_AVAILABLE"
    assert mtg.generic_current_authority_must_be_zero == (
        "asset_master_current",
        "forecasts_current",
        "recommendations_current",
        "risk_metrics_current",
    )

    assert contract.render_read_api_surfaces == (
        "global_status",
        "recommendations",
        "asset_detail",
        "domain_health",
        "lineage",
    )
    assert "transactions" in contract.application_state_not_part_of_dash_read_1
    assert "cash_balances" in contract.application_state_not_part_of_dash_read_1
    assert "user_target_policy" in contract.application_state_not_part_of_dash_read_1


def test_dash_read_1_contract_matches_fresh_uip_authority_schema(tmp_path: Path) -> None:
    config = _temp_config(tmp_path)
    initialize_database(config)
    contract = load_presentation_contract(ROOT)
    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        validate_authority_schema(connection, contract)
    finally:
        connection.close()


def test_dash_read_1_contract_fails_closed_if_synthesis_is_enabled(tmp_path: Path) -> None:
    source = json.loads((ROOT / CONTRACT_PATH).read_text(encoding="utf-8"))
    source["global_controls"]["missing_authority_may_be_synthesized"] = True
    candidate_root = tmp_path / "candidate"
    candidate_path = candidate_root / CONTRACT_PATH
    candidate_path.parent.mkdir(parents=True)
    candidate_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(PresentationContractError, match="missing_authority_may_be_synthesized"):
        load_presentation_contract(candidate_root)


def test_dash_read_1_contract_fails_closed_if_mtg_generic_authority_is_relaxed(tmp_path: Path) -> None:
    source = json.loads((ROOT / CONTRACT_PATH).read_text(encoding="utf-8"))
    source["domains"]["mtg"]["generic_current_authority_must_be_zero"] = [
        "asset_master_current"
    ]
    candidate_root = tmp_path / "candidate"
    candidate_path = candidate_root / CONTRACT_PATH
    candidate_path.parent.mkdir(parents=True)
    candidate_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(PresentationContractError, match="MTG generic-current suppression"):
        load_presentation_contract(candidate_root)
