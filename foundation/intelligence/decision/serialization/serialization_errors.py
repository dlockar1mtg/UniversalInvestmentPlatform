"""Exceptions raised by decision serialization and reconstruction."""


class DecisionSerializationError(ValueError):
    """Base exception for serialization failures."""


class SerializationConfigurationError(DecisionSerializationError):
    """Raised when a serialization profile is invalid."""


class SerializationSchemaError(DecisionSerializationError):
    """Raised when serialized data violates the decision schema."""


class DecisionDeserializationError(DecisionSerializationError):
    """Raised when a decision cannot be reconstructed."""


class DecisionExportError(DecisionSerializationError):
    """Raised when a decision export cannot be written."""
