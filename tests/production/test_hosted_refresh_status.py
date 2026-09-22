from datetime import datetime, timezone

from foundation.production.hosted_refresh_status import build_refresh_status


class FakePresentationRepository:
    def domain_health(self):
        return (
            {
                "domain_id": "crypto",
                "certification_state": "CERTIFIED",
                "import_registry_status": "ACTIVE",
                "last_import_status": "IMPORTED",
                "last_imported_at_utc": "2026-09-21T18:00:00+00:00",
                "last_data_as_of_date": "2026-09-21",
                "last_package_id": "crypto-package",
                "last_run_id": "crypto-run",
                "last_import_id": "crypto-import",
                "contract_version": "1.0.0",
                "warning_count": 0,
                "error_count": 0,
            },
            {
                "domain_id": "metals",
                "certification_state": "CERTIFIED",
                "import_registry_status": "ACTIVE",
                "last_import_status": "IMPORTED",
                "last_imported_at_utc": "2026-09-21T19:00:00+00:00",
                "last_data_as_of_date": "2026-08-01",
                "last_package_id": "metals-package",
                "last_run_id": "metals-run",
                "last_import_id": "metals-import",
                "contract_version": "1.0.0",
                "warning_count": 0,
                "error_count": 0,
            },
            {
                "domain_id": "mtg",
                "certification_state": "CERTIFIED",
                "import_registry_status": "ACTIVE",
                "last_import_status": "IMPORTED",
                "last_imported_at_utc": "2026-09-21T20:00:00+00:00",
                "last_data_as_of_date": None,
                "last_package_id": "mtg-package",
                "last_run_id": "mtg-run",
                "last_import_id": "mtg-import",
                "contract_version": "1.0.0",
                "warning_count": 0,
                "error_count": 0,
            },
        )


def test_refresh_status_combines_active_authority_with_locked_cadence():
    document = build_refresh_status(
        FakePresentationRepository(),
        now=datetime(2026, 9, 22, 9, 0, tzinfo=timezone.utc),
    )
    assert document["status"] == "HEALTHY"
    assert document["freshness_status"] == "REVIEW"
    assert document["freshness_review_count"] == 2
    assert document["refresh_execution_owner"] == "GITHUB_ACTIONS_SOURCE_OWNED"
    assert document["manual_dispatch_available"] is False
    assert document["lifecycle"] == [
        "Requested",
        "Source Refresh",
        "Certification",
        "UIP Import",
        "Activation",
        "Complete",
    ]
    by_domain = {item["domain_id"]: item for item in document["items"]}
    assert by_domain["crypto"]["next_scheduled_run_utc"] == "2026-09-22T11:15:00+00:00"
    assert by_domain["metals"]["next_scheduled_run_utc"] == "2026-09-22T12:23:00+00:00"
    assert by_domain["mtg"]["next_scheduled_run_utc"] == "2026-09-22T12:15:00+00:00"
    assert by_domain["crypto"]["data_age_days"] == 1
    assert by_domain["crypto"]["freshness_state"] == "CURRENT"
    assert by_domain["crypto"]["freshness_max_age_days"] == 2
    assert by_domain["metals"]["data_age_days"] == 52
    assert by_domain["metals"]["freshness_state"] == "STALE"
    assert by_domain["mtg"]["freshness_state"] == "UNKNOWN"
    assert by_domain["mtg"]["data_age_days"] is None
    assert by_domain["mtg"]["data_as_of"] is None


def test_refresh_status_surfaces_failure_without_claiming_new_authority():
    class ReviewRepository(FakePresentationRepository):
        def domain_health(self):
            rows = [dict(item) for item in super().domain_health()]
            rows[0]["error_count"] = 1
            rows[0]["status_message"] = "Provider refresh failed"
            return tuple(rows)

    document = build_refresh_status(
        ReviewRepository(),
        now=datetime(2026, 9, 22, 9, 0, tzinfo=timezone.utc),
    )
    crypto = next(item for item in document["items"] if item["domain_id"] == "crypto")
    assert document["status"] == "REVIEW"
    assert crypto["health_state"] == "REVIEW"
    assert crypto["failure_summary"] == "Provider refresh failed"
    assert crypto["last_good_state_status"] == "LAST_GOOD_STATE_REMAINS_ACTIVE"
    assert crypto["refresh_request_available"] is False
