"""Production integration and live delivery surfaces."""

from .api import APIResponse, ProductionAPI
from .certification import Phase6CertificationReport, ProductionCertificationCheck, certify_phase_6
from .config import ProductionRuntimeConfig
from .contracts import AuditEvent, PersistedArtifact, ProductionRun, ProductionRunStatus
from .dashboard import DashboardService, DashboardSettings
from .delivery_certification import DeliveryCertificationCheck, Phase7CertificationReport, certify_phase_7
from .deployment import DatabaseBackupManager, DeploymentManifest, MigrationCoordinator, SchemaMigration, StartupResult, bootstrap_production
from .http_service import HTTPServiceSettings, build_repository, create_http_app
from .integration import ExternalDataProvider, ExternalDataRecord, IngestionPolicy, NormalizedDataBatch, ingest_provider
from .live_security import LiveSecuritySettings, install_live_security
from .metals_providers import CommodityObservationAdapter, ProviderCollectionPolicy, ProviderCollectionResult, collect_with_policy, ingest_commodity_observations
from .metals_final import certify_phase_8_metals, scan_runtime_isolation
from .metals_readiness import evaluate_metals_readiness, summarize_metals_readiness
from .metals_registry import (
    MetalsAsset, MetalsRegistry, MetalsRegistryError, MetalsVehicle, canonical_metals_asset_id,
    load_metals_registry, validate_adapter_crosswalk, validate_metals_registry,
)
from .metals_vehicles import (
    VehicleAllocation, VehicleCandidate, VehicleConstraint, VehicleSelectionError,
    VehicleSelectionPolicy, VehicleSelectionResult, load_vehicle_selection_policy,
    select_metals_vehicles,
)
from .observability import EventRecorder, HealthReport, MetricRegistry, OperationalEvent, SecuredProductionGateway, evaluate_health
from .operations import OperationalStatus, ShutdownController, collect_operational_status
from .persistence import SQLiteProductionRepository
from .portfolio import PortfolioCSVError, PortfolioCSVValidationError, PortfolioImportReport, PortfolioPosition, import_portfolio_csv, preview_portfolio_csv
from .postgres import PostgresProductionRepository
from .postgres_jobs import PostgresJobRepository
from .providers import (
    AlphaVantageProvider, CommodityObservation, EconomicObservation, EIAUraniumProvider,
    FREDProvider, MarketQuote, ProviderError, WorldBankCommodityProvider,
)
from .scheduling import JobStatus, RetryPolicy, ScheduledJob, SQLiteJobRepository, run_next_job
from .security import APIKeyAuthenticator, Permission, Principal, SecretReference, redact
from .worker import HandlerRegistry, HostedWorker, RecurringSchedule, WorkerHealth, WorkerSettings, build_job_repository, enqueue_schedule

__all__ = [
    "APIKeyAuthenticator", "APIResponse", "AlphaVantageProvider", "AuditEvent", "CommodityObservation",
    "CommodityObservationAdapter",
    "DashboardService", "DashboardSettings", "DatabaseBackupManager", "DeliveryCertificationCheck",
    "DeploymentManifest", "EIAUraniumProvider", "EconomicObservation", "EventRecorder",
    "ExternalDataProvider", "ExternalDataRecord", "FREDProvider", "HTTPServiceSettings", "HandlerRegistry",
    "HealthReport", "HostedWorker", "IngestionPolicy", "JobStatus", "LiveSecuritySettings", "MarketQuote",
    "MetalsAsset", "MetalsRegistry", "MetalsRegistryError", "MetalsVehicle", "MetricRegistry", "MigrationCoordinator", "NormalizedDataBatch", "OperationalEvent", "OperationalStatus",
    "Permission", "PersistedArtifact", "Phase6CertificationReport", "Phase7CertificationReport",
    "PortfolioCSVError", "PortfolioCSVValidationError", "PortfolioImportReport", "PortfolioPosition",
    "PostgresJobRepository", "PostgresProductionRepository", "Principal", "ProductionAPI",
    "ProductionCertificationCheck", "ProductionRun", "ProductionRunStatus", "ProductionRuntimeConfig",
    "ProviderCollectionPolicy", "ProviderCollectionResult", "ProviderError", "RecurringSchedule", "RetryPolicy", "SQLiteJobRepository", "SQLiteProductionRepository",
    "ScheduledJob", "SchemaMigration", "SecuredProductionGateway", "SecretReference", "ShutdownController",
    "StartupResult", "VehicleAllocation", "VehicleCandidate", "VehicleConstraint", "VehicleSelectionError",
    "VehicleSelectionPolicy", "VehicleSelectionResult", "WorkerHealth", "WorkerSettings",
    "WorldBankCommodityProvider", "bootstrap_production",
    "build_job_repository", "build_repository", "canonical_metals_asset_id", "certify_phase_6", "certify_phase_7",
    "certify_phase_8_metals", "collect_with_policy",
    "collect_operational_status", "create_http_app", "enqueue_schedule", "evaluate_health",
    "evaluate_metals_readiness",
    "import_portfolio_csv", "ingest_commodity_observations", "ingest_provider", "install_live_security",
    "load_metals_registry", "load_vehicle_selection_policy",
    "preview_portfolio_csv", "redact", "scan_runtime_isolation", "select_metals_vehicles",
    "summarize_metals_readiness",
    "validate_adapter_crosswalk",
    "validate_metals_registry",
    "run_next_job",
]
