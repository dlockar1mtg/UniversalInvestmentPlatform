"""Governed presentation/read-model boundary for UIP dashboard services."""

from .read_model_contracts import (
    CONTRACT_PATH,
    EXPECTED_DOMAINS,
    PresentationContractError,
    PresentationReadModelContract,
    load_presentation_contract,
    validate_authority_schema,
)

__all__ = [
    "CONTRACT_PATH",
    "EXPECTED_DOMAINS",
    "PresentationContractError",
    "PresentationReadModelContract",
    "load_presentation_contract",
    "validate_authority_schema",
]
