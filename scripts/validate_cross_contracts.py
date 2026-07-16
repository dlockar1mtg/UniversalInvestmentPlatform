from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = (
    ROOT
    / "data"
    / "integration"
    / "uiip_integration.duckdb"
)
SETTINGS_PATH = (
    ROOT
    / "config"
    / "validation"
    / "validation_settings.json"
)
REPORT_PATH = (
    ROOT
    / "data"
    / "validation"
    / "phase_0_6_cross_contract_validation.json"
)

sys.path.insert(0, str(ROOT))

from validation.findings import (  # noqa: E402
    ValidationFinding,
    has_failures,
    severity_counts,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        raise FileNotFoundError(
            f"Validation settings not found: {SETTINGS_PATH}"
        )

    return json.loads(
        SETTINGS_PATH.read_text(encoding="utf-8")
    )


def table_exists(
    connection: duckdb.DuckDBPyConnection,
    schema_name: str,
    table_name: str,
) -> bool:
    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = ?
          AND table_name = ?
        """,
        [schema_name, table_name],
    ).fetchone()[0]

    return count > 0


def validate_database_version(
    connection: duckdb.DuckDBPyConnection,
    settings: dict,
) -> list[ValidationFinding]:
    expected_version = settings["database_version"]

    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM meta.database_version
        WHERE version = ?
        """,
        [expected_version],
    ).fetchone()[0]

    if count > 0:
        return []

    return [
        ValidationFinding(
            validation_id="DB-VERSION-001",
            category="database",
            severity="critical",
            message=(
                f"Expected database version "
                f"{expected_version} is not recorded."
            ),
            suggested_action=(
                "Run initialize_integration_db.py using "
                "the current repository version."
            ),
        )
    ]


def validate_contract_versions(
    connection: duckdb.DuckDBPyConnection,
    settings: dict,
) -> list[ValidationFinding]:
    supported = settings["supported_contract_versions"]
    findings: list[ValidationFinding] = []

    contract_tables = [
        "platform_status",
        "asset_master",
        "recommendations",
        "forecasts",
        "risk_metrics",
        "portfolio_positions",
        "macro_signals",
        "export_manifest",
    ]

    for table_name in contract_tables:
        if not table_exists(
            connection,
            "contracts",
            table_name,
        ):
            continue

        rows = connection.execute(
            f"""
            SELECT DISTINCT contract_version
            FROM contracts.{table_name}
            WHERE contract_version IS NOT NULL
            """
        ).fetchall()

        for (version,) in rows:
            if version not in supported:
                findings.append(
                    ValidationFinding(
                        validation_id="CONTRACT-VERSION-001",
                        category="contract_version",
                        severity="critical",
                        contract_name=table_name,
                        message=(
                            f"Unsupported contract version "
                            f"{version!r} found in "
                            f"contracts.{table_name}."
                        ),
                        suggested_action=(
                            "Migrate the export or add explicit "
                            "version compatibility."
                        ),
                    )
                )

    return findings


def validate_recommendation_assets(
    connection: duckdb.DuckDBPyConnection,
) -> list[ValidationFinding]:
    rows = connection.execute(
        """
        SELECT DISTINCT
            r.platform_id,
            r.run_id,
            r.universal_asset_id
        FROM contracts.recommendations r
        LEFT JOIN contracts.asset_master a
            ON r.platform_id = a.platform_id
           AND r.run_id = a.run_id
           AND r.universal_asset_id =
               a.universal_asset_id
        WHERE a.universal_asset_id IS NULL
        """
    ).fetchall()

    return [
        ValidationFinding(
            validation_id="REFERENTIAL-REC-001",
            category="referential_integrity",
            severity="error",
            platform_id=platform_id,
            run_id=run_id,
            contract_name="recommendations",
            record_identifier=asset_id,
            message=(
                "Recommendation does not reference a matching "
                "asset-master record from the same platform run."
            ),
            suggested_action=(
                "Publish or import the corresponding asset-master "
                "record before the recommendation."
            ),
        )
        for platform_id, run_id, asset_id in rows
    ]


def validate_forecast_assets(
    connection: duckdb.DuckDBPyConnection,
) -> list[ValidationFinding]:
    rows = connection.execute(
        """
        SELECT DISTINCT
            f.platform_id,
            f.run_id,
            f.universal_asset_id
        FROM contracts.forecasts f
        LEFT JOIN contracts.asset_master a
            ON f.platform_id = a.platform_id
           AND f.run_id = a.run_id
           AND f.universal_asset_id =
               a.universal_asset_id
        WHERE a.universal_asset_id IS NULL
        """
    ).fetchall()

    return [
        ValidationFinding(
            validation_id="REFERENTIAL-FCST-001",
            category="referential_integrity",
            severity="error",
            platform_id=platform_id,
            run_id=run_id,
            contract_name="forecasts",
            record_identifier=asset_id,
            message=(
                "Forecast does not reference a matching "
                "asset-master record from the same platform run."
            ),
            suggested_action=(
                "Publish or import the corresponding asset-master "
                "record before the forecast."
            ),
        )
        for platform_id, run_id, asset_id in rows
    ]


def validate_risk_assets(
    connection: duckdb.DuckDBPyConnection,
) -> list[ValidationFinding]:
    rows = connection.execute(
        """
        SELECT DISTINCT
            r.platform_id,
            r.run_id,
            r.universal_asset_id
        FROM contracts.risk_metrics r
        LEFT JOIN contracts.asset_master a
            ON r.platform_id = a.platform_id
           AND r.run_id = a.run_id
           AND r.universal_asset_id =
               a.universal_asset_id
        WHERE a.universal_asset_id IS NULL
        """
    ).fetchall()

    return [
        ValidationFinding(
            validation_id="REFERENTIAL-RISK-001",
            category="referential_integrity",
            severity="error",
            platform_id=platform_id,
            run_id=run_id,
            contract_name="risk_metrics",
            record_identifier=asset_id,
            message=(
                "Risk metric does not reference a matching "
                "asset-master record from the same platform run."
            ),
            suggested_action=(
                "Publish or import the corresponding asset-master "
                "record before the risk record."
            ),
        )
        for platform_id, run_id, asset_id in rows
    ]


def validate_registered_platforms(
    connection: duckdb.DuckDBPyConnection,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    tables = [
        "platform_status",
        "asset_master",
        "recommendations",
        "forecasts",
        "risk_metrics",
        "macro_signals",
        "export_manifest",
    ]

    for table_name in tables:
        rows = connection.execute(
            f"""
            SELECT DISTINCT c.platform_id
            FROM contracts.{table_name} c
            LEFT JOIN registry.platforms p
                ON c.platform_id = p.platform_id
            WHERE p.platform_id IS NULL
            """
        ).fetchall()

        for (platform_id,) in rows:
            findings.append(
                ValidationFinding(
                    validation_id="REGISTRY-PLATFORM-001",
                    category="registry_consistency",
                    severity="error",
                    platform_id=platform_id,
                    contract_name=table_name,
                    message=(
                        f"Contract table {table_name} contains "
                        f"unregistered platform {platform_id!r}."
                    ),
                    suggested_action=(
                        "Register the platform before importing "
                        "its contract exports."
                    ),
                )
            )

    return findings


def validate_score_ranges(
    connection: duckdb.DuckDBPyConnection,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    recommendation_rows = connection.execute(
        """
        SELECT
            platform_id,
            run_id,
            universal_asset_id,
            normalized_score,
            confidence_score
        FROM contracts.recommendations
        WHERE normalized_score < 0
           OR normalized_score > 100
           OR confidence_score < 0
           OR confidence_score > 100
        """
    ).fetchall()

    for (
        platform_id,
        run_id,
        asset_id,
        score,
        confidence,
    ) in recommendation_rows:
        findings.append(
            ValidationFinding(
                validation_id="RANGE-REC-001",
                category="range",
                severity="error",
                platform_id=platform_id,
                run_id=run_id,
                contract_name="recommendations",
                record_identifier=asset_id,
                message=(
                    "Recommendation score or confidence is "
                    "outside the allowed 0-to-100 range: "
                    f"score={score}, confidence={confidence}."
                ),
                suggested_action=(
                    "Normalize scores before publishing."
                ),
            )
        )

    risk_rows = connection.execute(
        """
        SELECT
            platform_id,
            run_id,
            universal_asset_id,
            risk_score
        FROM contracts.risk_metrics
        WHERE risk_score < 0
           OR risk_score > 100
        """
    ).fetchall()

    for platform_id, run_id, asset_id, score in risk_rows:
        findings.append(
            ValidationFinding(
                validation_id="RANGE-RISK-001",
                category="range",
                severity="error",
                platform_id=platform_id,
                run_id=run_id,
                contract_name="risk_metrics",
                record_identifier=asset_id,
                message=(
                    f"Risk score {score} is outside the "
                    "allowed 0-to-100 range."
                ),
                suggested_action=(
                    "Normalize the risk score before publishing."
                ),
            )
        )

    return findings


def validate_weight_order(
    connection: duckdb.DuckDBPyConnection,
) -> list[ValidationFinding]:
    rows = connection.execute(
        """
        SELECT
            platform_id,
            run_id,
            universal_asset_id,
            minimum_weight,
            target_weight,
            maximum_weight
        FROM contracts.recommendations
        WHERE (
            minimum_weight IS NOT NULL
            AND target_weight IS NOT NULL
            AND minimum_weight > target_weight
        )
        OR (
            target_weight IS NOT NULL
            AND maximum_weight IS NOT NULL
            AND target_weight > maximum_weight
        )
        """
    ).fetchall()

    return [
        ValidationFinding(
            validation_id="WEIGHT-ORDER-001",
            category="business_rule",
            severity="error",
            platform_id=platform_id,
            run_id=run_id,
            contract_name="recommendations",
            record_identifier=asset_id,
            message=(
                "Recommendation weights are not ordered as "
                "minimum <= target <= maximum: "
                f"minimum={minimum_weight}, "
                f"target={target_weight}, "
                f"maximum={maximum_weight}."
            ),
            suggested_action=(
                "Correct the recommendation allocation bounds."
            ),
        )
        for (
            platform_id,
            run_id,
            asset_id,
            minimum_weight,
            target_weight,
            maximum_weight,
        ) in rows
    ]


def validate_import_audit_counts(
    connection: duckdb.DuckDBPyConnection,
) -> list[ValidationFinding]:
    rows = connection.execute(
        """
        SELECT
            import_batch_id,
            contract_name,
            source_record_count,
            imported_record_count,
            rejected_record_count
        FROM meta.import_runs
        WHERE source_record_count !=
              imported_record_count + rejected_record_count
        """
    ).fetchall()

    return [
        ValidationFinding(
            validation_id="IMPORT-AUDIT-001",
            category="import_audit",
            severity="error",
            contract_name=contract_name,
            record_identifier=import_batch_id,
            message=(
                "Import audit counts do not reconcile: "
                f"source={source_count}, "
                f"imported={imported_count}, "
                f"rejected={rejected_count}."
            ),
            suggested_action=(
                "Review the importer and regenerate the audit row."
            ),
        )
        for (
            import_batch_id,
            contract_name,
            source_count,
            imported_count,
            rejected_count,
        ) in rows
    ]


def validate_duplicate_logical_keys(
    connection: duckdb.DuckDBPyConnection,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    duplicate_assets = connection.execute(
        """
        SELECT
            platform_id,
            run_id,
            universal_asset_id,
            COUNT(*) AS duplicate_count
        FROM contracts.asset_master
        GROUP BY
            platform_id,
            run_id,
            universal_asset_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    for platform_id, run_id, asset_id, count in duplicate_assets:
        findings.append(
            ValidationFinding(
                validation_id="DUPLICATE-ASSET-001",
                category="duplicate_key",
                severity="error",
                platform_id=platform_id,
                run_id=run_id,
                contract_name="asset_master",
                record_identifier=asset_id,
                message=(
                    f"Duplicate logical asset-master key "
                    f"appears {count} times."
                ),
                suggested_action=(
                    "Remove duplicate records before importing."
                ),
            )
        )

    duplicate_recommendations = connection.execute(
        """
        SELECT
            platform_id,
            run_id,
            universal_asset_id,
            as_of_date,
            COALESCE(time_horizon, ''),
            COUNT(*) AS duplicate_count
        FROM contracts.recommendations
        GROUP BY
            platform_id,
            run_id,
            universal_asset_id,
            as_of_date,
            COALESCE(time_horizon, '')
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    for (
        platform_id,
        run_id,
        asset_id,
        as_of_date,
        time_horizon,
        count,
    ) in duplicate_recommendations:
        findings.append(
            ValidationFinding(
                validation_id="DUPLICATE-REC-001",
                category="duplicate_key",
                severity="error",
                platform_id=platform_id,
                run_id=run_id,
                contract_name="recommendations",
                record_identifier=asset_id,
                message=(
                    f"Duplicate recommendation key appears "
                    f"{count} times for date {as_of_date} and "
                    f"horizon {time_horizon!r}."
                ),
                suggested_action=(
                    "Remove duplicates or introduce an explicit "
                    "model identifier in a future contract."
                ),
            )
        )

    return findings


def write_report(
    findings: list[ValidationFinding],
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "validation_version": "1.0.0",
        "generated_at_utc": utc_now_iso(),
        "database_path": str(DATABASE_PATH),
        "valid": not has_failures(findings),
        "severity_counts": severity_counts(findings),
        "findings": [
            finding.to_dict()
            for finding in findings
        ],
    }

    REPORT_PATH.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    try:
        settings = load_settings()

        if not DATABASE_PATH.exists():
            finding = ValidationFinding(
                validation_id="DB-AVAILABLE-001",
                category="database",
                severity="critical",
                message=(
                    "Integration database does not exist."
                ),
                suggested_action=(
                    "Run run_phase_0_5_smoke_test.py "
                    "or initialize_integration_db.py."
                ),
            )

            write_report([finding])
            print("Cross-contract validation failed.")
            print(f"  CRITICAL: {finding.message}")
            return 1

        findings: list[ValidationFinding] = []

        with duckdb.connect(
            str(DATABASE_PATH),
            read_only=True,
        ) as connection:
            findings.extend(
                validate_database_version(
                    connection,
                    settings,
                )
            )
            findings.extend(
                validate_contract_versions(
                    connection,
                    settings,
                )
            )
            findings.extend(
                validate_recommendation_assets(connection)
            )
            findings.extend(
                validate_forecast_assets(connection)
            )
            findings.extend(
                validate_risk_assets(connection)
            )
            findings.extend(
                validate_registered_platforms(connection)
            )
            findings.extend(
                validate_score_ranges(connection)
            )
            findings.extend(
                validate_weight_order(connection)
            )
            findings.extend(
                validate_import_audit_counts(connection)
            )
            findings.extend(
                validate_duplicate_logical_keys(connection)
            )

        write_report(findings)

        counts = severity_counts(findings)

        print("Cross-contract validation")
        print("=" * 72)
        print(f"Info findings: {counts['info']}")
        print(f"Warnings: {counts['warning']}")
        print(f"Errors: {counts['error']}")
        print(f"Critical findings: {counts['critical']}")

        for finding in findings:
            print(
                f"{finding.severity.upper()}: "
                f"{finding.validation_id} — "
                f"{finding.message}"
            )

        if has_failures(findings):
            print("\nCross-contract validation failed.")
            return 1

        print("\nCross-contract validation passed.")
        print(f"Validation report: {REPORT_PATH}")
        return 0

    except Exception as exc:
        print(
            f"Unexpected validation failure: {exc}",
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())