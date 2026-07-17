"""Lifecycle and eligibility statuses for investment decisions."""

from enum import StrEnum


class DecisionStatus(StrEnum):
    """Current lifecycle status of a decision record."""

    DRAFT = "draft"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    CERTIFIED = "certified"


class EligibilityStatus(StrEnum):
    """Eligibility outcome produced before action classification."""

    ELIGIBLE = "eligible"
    CONDITIONALLY_ELIGIBLE = "conditionally_eligible"
    INELIGIBLE = "ineligible"
    INSUFFICIENT_DATA = "insufficient_data"
