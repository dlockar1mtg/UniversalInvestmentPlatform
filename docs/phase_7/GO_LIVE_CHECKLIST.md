# Phase 7 Go-Live Checklist

- Select the hosting platform, region, and production domain.
- Provision managed PostgreSQL with backups and restricted network access.
- Store API, provider, and database credentials in the host secret manager.
- Configure `UIIP_ALLOWED_HOSTS`, HTTPS enforcement, and the public health endpoint.
- Deploy the candidate to staging and import a copy of the holdings CSV through the approved private process.
- Verify API, worker, scheduler, dashboard, provider, backup, and restore behavior in staging.
- Run the complete test suite and `scripts/certify_phase_7.py` at the release commit.
- Protect the GitHub staging and production environments with required reviewers.
- Invoke **Phase 7 Go-Live Gate**, choose the target, and type `DEPLOY` only after approval.
- Record the image digest, migration result, certification artifact, rollback target, and release timestamp.
