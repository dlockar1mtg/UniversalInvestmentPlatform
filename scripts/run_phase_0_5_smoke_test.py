from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "integration" / "uiip_integration.duckdb"


def run_script(
    script_name: str,
    *arguments: str,
    expected_codes: tuple[int, ...] = (0,),
) -> None:
    script_path = ROOT / "scripts" / script_name

    print(f"\nRunning {script_name}")
    print("=" * 72)

    result = subprocess.run(
        [sys.executable, str(script_path), *arguments],
        cwd=ROOT,
        check=False,
    )

    if result.returncode not in expected_codes:
        raise SystemExit(
            f"{script_name} failed with exit code "
            f"{result.returncode}"
        )


def verify_database() -> None:
    with duckdb.connect(str(DATABASE_PATH)) as connection:
        values = {
            "machines": connection.execute(
                "SELECT COUNT(*) FROM registry.machines"
            ).fetchone()[0],
            "platforms": connection.execute(
                "SELECT COUNT(*) FROM registry.platforms"
            ).fetchone()[0],
            "assets": connection.execute(
                "SELECT COUNT(*) FROM contracts.asset_master"
            ).fetchone()[0],
            "recommendations": connection.execute(
                "SELECT COUNT(*) FROM contracts.recommendations"
            ).fetchone()[0],
            "asset_intelligence": connection.execute(
                "SELECT COUNT(*) FROM analytics.asset_intelligence"
            ).fetchone()[0],
            "successful_imports": connection.execute(
                """
                SELECT COUNT(*)
                FROM meta.import_runs
                WHERE import_status = 'success'
                """
            ).fetchone()[0],
        }

    expected = {
        "machines": 3,
        "platforms": 8,
        "assets": 3,
        "recommendations": 3,
        "asset_intelligence": 3,
        "successful_imports": 2,
    }

    failures: list[str] = []

    for name, expected_value in expected.items():
        actual = values[name]
        status = "PASS" if actual == expected_value else "FAIL"

        print(
            f"{status}: {name} = {actual} "
            f"(expected {expected_value})"
        )

        if actual != expected_value:
            failures.append(
                f"{name}: expected {expected_value}, found {actual}"
            )

    if failures:
        raise SystemExit(
            "Database verification failed:\n- "
            + "\n- ".join(failures)
        )


def verify_duplicate_protection() -> None:
    run_script(
        "import_contract_csv.py",
        "schemas/v1/examples/asset_master_example.csv",
    )

    with duckdb.connect(str(DATABASE_PATH)) as connection:
        asset_count = connection.execute(
            "SELECT COUNT(*) FROM contracts.asset_master"
        ).fetchone()[0]

        import_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM meta.import_runs
            WHERE contract_name = 'asset_master'
              AND import_status = 'success'
            """
        ).fetchone()[0]

    if asset_count != 3 or import_count != 1:
        raise SystemExit(
            "Duplicate-import protection failed: "
            f"asset_count={asset_count}, import_count={import_count}"
        )

    print("PASS: duplicate-import protection")


def main() -> None:
    run_script("reset_integration_db.py", "--confirm")
    run_script("initialize_integration_db.py")
    run_script("load_registry_to_db.py")

    run_script(
        "import_contract_csv.py",
        "schemas/v1/examples/asset_master_example.csv",
    )

    run_script(
        "import_contract_csv.py",
        "schemas/v1/examples/recommendations_example.csv",
    )

    print("\nVerifying integration database")
    print("=" * 72)
    verify_database()

    print("\nVerifying duplicate-import protection")
    print("=" * 72)
    verify_duplicate_protection()

    run_script("validate_integration_db.py")

    print("\nPhase 0.5 integration smoke test completed successfully.")


if __name__ == "__main__":
    main()