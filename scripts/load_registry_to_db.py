from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "integration" / "uiip_integration.duckdb"

PLATFORM_REGISTRY_PATH = (
    ROOT / "registry" / "v1" / "data" / "platform_registry.csv"
)
MACHINE_REGISTRY_PATH = (
    ROOT / "registry" / "v1" / "data" / "machine_registry.csv"
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_boolean(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
                "yes": True,
                "no": False,
            }
        )
    )


def load_machine_registry(connection: duckdb.DuckDBPyConnection) -> int:
    frame = pd.read_csv(MACHINE_REGISTRY_PATH, dtype=str).fillna("")

    frame["git_available"] = normalize_boolean(frame["git_available"])
    frame["last_verified_date"] = pd.to_datetime(
        frame["last_verified_date"],
        errors="coerce",
    ).dt.date
    frame["loaded_at_utc"] = utc_now()

    connection.execute("DELETE FROM registry.machines")
    connection.register("machine_registry_frame", frame)

    connection.execute(
        """
        INSERT INTO registry.machines
        SELECT
            registry_version,
            machine_id,
            machine_name,
            machine_role,
            NULLIF(operating_system, ''),
            NULLIF(python_version, ''),
            git_available,
            NULLIF(archive_support, ''),
            availability_status,
            NULLIF(sync_method, ''),
            last_verified_date,
            NULLIF(notes, ''),
            loaded_at_utc
        FROM machine_registry_frame
        """
    )

    connection.unregister("machine_registry_frame")
    return len(frame)


def load_platform_registry(connection: duckdb.DuckDBPyConnection) -> int:
    frame = pd.read_csv(PLATFORM_REGISTRY_PATH, dtype=str).fillna("")

    frame["is_enabled"] = normalize_boolean(frame["is_enabled"])

    frame["freshness_threshold_hours"] = pd.to_numeric(
        frame["freshness_threshold_hours"],
        errors="coerce",
    ).astype("Int64")

    frame["last_verified_date"] = pd.to_datetime(
        frame["last_verified_date"],
        errors="coerce",
    ).dt.date

    frame["last_successful_run_at_utc"] = pd.to_datetime(
        frame["last_successful_run_at_utc"],
        errors="coerce",
        utc=True,
    ).dt.tz_localize(None)

    frame["loaded_at_utc"] = utc_now()

    connection.execute("DELETE FROM registry.platforms")
    connection.register("platform_registry_frame", frame)

    connection.execute(
        """
        INSERT INTO registry.platforms
        SELECT
            registry_version,
            platform_id,
            platform_name,
            repository_name,
            NULLIF(local_path, ''),
            machine_id,
            NULLIF(platform_version, ''),
            platform_status,
            integration_stage,
            NULLIF(primary_database, ''),
            NULLIF(main_run_command, ''),
            NULLIF(validation_command, ''),
            NULLIF(dashboard_command, ''),
            exchange_folder,
            NULLIF(published_contracts, ''),
            expected_refresh_frequency,
            freshness_threshold_hours,
            last_verified_date,
            last_successful_run_at_utc,
            NULLIF(known_issue, ''),
            NULLIF(github_repository, ''),
            is_enabled,
            NULLIF(notes, ''),
            loaded_at_utc
        FROM platform_registry_frame
        """
    )

    connection.unregister("platform_registry_frame")
    return len(frame)


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            "Integration database does not exist. "
            "Run initialize_integration_db.py first."
        )

    with duckdb.connect(str(DATABASE_PATH)) as connection:
        machine_count = load_machine_registry(connection)
        platform_count = load_platform_registry(connection)

    print("Registry loaded into integration database.")
    print(f"Machines loaded: {machine_count}")
    print(f"Platforms loaded: {platform_count}")


if __name__ == "__main__":
    main()