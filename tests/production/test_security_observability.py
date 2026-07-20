from datetime import datetime, timezone
import json

from foundation.production import (
    APIKeyAuthenticator, EventRecorder, MetricRegistry, Permission, ProductionAPI,
    SQLiteProductionRepository, SecuredProductionGateway, SecretReference,
    evaluate_health, redact,
)

NOW = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)


def gateway(tmp_path):
    repo = SQLiteProductionRepository(tmp_path / "production.sqlite3")
    repo.initialize()
    auth = APIKeyAuthenticator(
        {"viewer-1": ("viewer",), "operator-1": ("operator",)},
        {"viewer-1": APIKeyAuthenticator.hash_credential("view-key"), "operator-1": APIKeyAuthenticator.hash_credential("operate-key")},
    )
    events, metrics = EventRecorder(), MetricRegistry()
    return SecuredProductionGateway(ProductionAPI(repo), auth, events, metrics), events, metrics


def request():
    return json.dumps({"run_id": "run-1", "source_phase": "5.5", "policy_fingerprint": "a" * 64, "requested_at": NOW.isoformat(), "payload": {"portfolio": "universal"}})


def test_authentication_uses_digest_identity_and_roles():
    auth = APIKeyAuthenticator({"operator": ("operator",)}, {"operator": APIKeyAuthenticator.hash_credential("key")})
    principal = auth.authenticate("key")
    assert principal.principal_id == "operator"
    assert principal.permits(Permission.RUN_SUBMIT)
    assert auth.authenticate("wrong") is None


def test_gateway_enforces_authentication_and_authorization(tmp_path):
    service, _, _ = gateway(tmp_path)
    assert service.handle("POST", "/v1/runs", request(), correlation_id="c1").status_code == 401
    assert service.handle("POST", "/v1/runs", request(), credential="view-key", correlation_id="c2").status_code == 403
    assert service.handle("POST", "/v1/runs", request(), credential="operate-key", correlation_id="c3").status_code == 202
    assert service.handle("GET", "/v1/runs/run-1", credential="view-key", correlation_id="c4").status_code == 200


def test_secrets_are_reference_only_and_sensitive_fields_are_redacted():
    reference = SecretReference("UIIP_API_KEY")
    assert reference.resolve({"UIIP_API_KEY": "top-secret"}) == "top-secret"
    safe = redact({"api_key": "top-secret", "nested": {"access_token": "token", "value": 1}})
    assert safe["api_key"] == "[REDACTED]"
    assert safe["nested"]["access_token"] == "[REDACTED]"
    assert "top-secret" not in repr(reference)


def test_operational_events_preserve_correlation_and_redact_credentials(tmp_path):
    service, events, _ = gateway(tmp_path)
    service.handle("GET", "/v1/runs/missing", credential="view-key", correlation_id="correlation-1")
    event = events.events[0]
    assert event.correlation_id == "correlation-1"
    assert event.fields["credential"] == "[REDACTED]"
    assert event.fields["principal_id"] == "viewer-1"


def test_metrics_are_deterministic_and_partitioned_by_status(tmp_path):
    service, _, metrics = gateway(tmp_path)
    service.handle("GET", "/v1/runs/missing", correlation_id="c1")
    service.handle("GET", "/v1/runs/missing", credential="view-key", correlation_id="c2")
    snapshot = metrics.snapshot()
    assert tuple(item["labels"]["status"] for item in snapshot["counters"]) == ("401", "404")
    assert all(item["value"] == 1 for item in snapshot["counters"])


def test_health_reports_liveness_and_dependency_readiness_without_raising():
    healthy = evaluate_health({"database": lambda: True, "scheduler": lambda: True})
    degraded = evaluate_health({"database": lambda: True, "scheduler": lambda: (_ for _ in ()).throw(RuntimeError("down"))})
    assert healthy.live and healthy.ready
    assert degraded.live and not degraded.ready
    assert degraded.checks["scheduler"] is False
