"""Exceptions raised by universal action classification."""


class ActionClassificationError(ValueError):
    """Base exception for action-classification failures."""


class ClassificationInputError(ActionClassificationError):
    """Raised when classification inputs are inconsistent."""
