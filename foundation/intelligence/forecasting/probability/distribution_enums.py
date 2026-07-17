"""Enumerations for probabilistic forecast distributions."""

from __future__ import annotations

from enum import Enum


class StringEnum(str, Enum):
    """String-valued enum with natural serialization."""

    def __str__(self) -> str:
        return self.value


class DistributionFamily(StringEnum):
    """Supported distribution families and generation mechanisms."""

    EMPIRICAL = "empirical"
    NORMAL = "normal"
    LOGNORMAL = "lognormal"
    STUDENT_T = "student_t"
    BETA = "beta"
    GAMMA = "gamma"
    MIXTURE = "mixture"
    MONTE_CARLO = "monte_carlo"
    BAYESIAN_POSTERIOR = "bayesian_posterior"
    SCENARIO_TREE = "scenario_tree"
    CUSTOM = "custom"


class DistributionStatus(StringEnum):
    """Lifecycle state of a probabilistic forecast distribution."""

    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"
    FAILED = "failed"


class TailRiskSide(StringEnum):
    """Tail of the return distribution being summarized."""

    LOWER = "lower"
    UPPER = "upper"
    BOTH = "both"
