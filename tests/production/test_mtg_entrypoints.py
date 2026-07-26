from foundation.production.mtg.entrypoints import resolve_entrypoints


def _row(path: str, capabilities: list[str], score: int = 40) -> dict[str, object]:
    return {
        "path": path,
        "capabilities": capabilities,
        "executable": True,
        "score": score,
    }


def test_resolver_prefers_certified_export_and_closeout() -> None:
    payload = {
        "candidates": [
            _row("scripts/build_phase_10_10_universal_export.py", ["EXPORT"], 59),
            _row("scripts/build_universal_export_old.py", ["EXPORT"], 80),
            _row("scripts/certify_phase_10_9_unified_mtg_closeout.py", ["CERTIFICATION"], 49),
            _row("scripts/run_production_closeout.py", ["CERTIFICATION"], 60),
            _row("collectors/ebay_collector.py", ["EBAY"], 40),
            _row("collectors/tcgcsv_collector.py", ["TCGPLAYER"], 40),
        ]
    }
    report = resolve_entrypoints(payload)
    assert report.status == "PASS"
    assert report.selections["UNIVERSAL_EXPORT"].path.endswith("build_phase_10_10_universal_export.py")
    assert report.selections["PRODUCTION_CLOSEOUT"].path.endswith("certify_phase_10_9_unified_mtg_closeout.py")


def test_resolver_excludes_installers_apply_scripts_and_tests() -> None:
    payload = {
        "candidates": [
            _row("scripts/apply_ebay_collection_bundle.py", ["EBAY"], 100),
            _row("tests/test_ebay_collection.py", ["EBAY"], 100),
            _row("collectors/ebay_collector.py", ["EBAY"], 20),
            _row("scripts/build_phase_10_10_universal_export.py", ["EXPORT"], 20),
            _row("scripts/certify_phase_10_9_unified_mtg_closeout.py", ["CERTIFICATION"], 20),
            _row("collectors/tcgcsv_collector.py", ["TCGPLAYER"], 20),
        ]
    }
    report = resolve_entrypoints(payload)
    assert report.selections["EBAY_COLLECTION"].path == "collectors/ebay_collector.py"


def test_resolver_rejects_certification_scripts_as_collectors_and_init_as_forecast() -> None:
    payload = {
        "candidates": [
            _row("scripts/build_phase_10_10_universal_export.py", ["EXPORT"], 20),
            _row("scripts/certify_phase_10_9_unified_mtg_closeout.py", ["CERTIFICATION"], 20),
            _row("scripts/certify_collector_booster_box_production_closeout.py", ["EBAY", "TCGPLAYER"], 100),
            _row("terminal2/forecast/__init__.py", ["FORECAST"], 100),
        ]
    }
    report = resolve_entrypoints(payload)
    assert report.status == "INCOMPLETE"
    assert "EBAY_COLLECTION" not in report.selections
    assert "TCGPLAYER_COLLECTION" not in report.selections
    assert "FORECAST" not in report.selections


def test_resolver_fails_closed_when_required_roles_are_missing() -> None:
    report = resolve_entrypoints({"candidates": [_row("scripts/run_forecast.py", ["FORECAST"]) ]})
    assert report.status == "INCOMPLETE"
    assert any(code.startswith("REQUIRED_ENTRYPOINT_UNRESOLVED") for code in report.reason_codes)
