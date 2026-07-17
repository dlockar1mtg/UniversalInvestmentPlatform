"""Custom exceptions for the Universal Import Engine."""


class ImportEngineError(Exception):
    """Base exception for import-engine failures."""


class PackageNotFoundError(ImportEngineError):
    """Raised when an integration package cannot be located."""


class ManifestError(ImportEngineError):
    """Raised when the export manifest is missing or invalid."""


class ChecksumError(ImportEngineError):
    """Raised when a package checksum does not match."""


class ContractValidationError(ImportEngineError):
    """Raised when a dataset violates a Universal contract."""


class DuplicatePackageError(ImportEngineError):
    """Raised when a package has already been imported."""


class UnsupportedPlatformError(ImportEngineError):
    """Raised when a package references an unregistered platform."""


class ImportTransactionError(ImportEngineError):
    """Raised when a transactional load fails."""