from pathlib import Path

from foundation.production.mtg.source_audit import audit_source, publish_source_audit


def test_missing_source_fails_closed(tmp_path: Path) -> None:
    report = audit_source(tmp_path / "missing")
    assert report.status == "FAILED"
    assert "MTG_SOURCE_ROOT_NOT_AVAILABLE" in report.reason_codes


def test_capabilities_are_discovered_without_execution(tmp_path: Path) -> None:
    source = tmp_path / "mtg"
    (source / "scripts").mkdir(parents=True)
    (source / "scripts" / "collect_ebay_prices.py").write_text("# ebay active listings", encoding="utf-8")
    (source / "scripts" / "collect_tcgcsv.py").write_text("# tcgplayer tcgcsv", encoding="utf-8")
    (source / "scripts" / "export_universal.py").write_text("# export_manifest package_summary", encoding="utf-8")
    (source / "scripts" / "certify_production.py").write_text("# certification production_closed", encoding="utf-8")

    report = audit_source(source)
    assert report.status == "PASS"
    assert report.capability_counts["EBAY"] >= 1
    assert report.capability_counts["TCGPLAYER"] >= 1
    assert report.capability_counts["EXPORT"] >= 1
    assert report.capability_counts["CERTIFICATION"] >= 1


def test_audit_report_is_published(tmp_path: Path) -> None:
    source = tmp_path / "mtg"
    source.mkdir()
    (source / "ebay.md").write_text("ebay", encoding="utf-8")
    report = audit_source(source)
    output = publish_source_audit(report, tmp_path / "out" / "latest.json")
    assert output.is_file()
    assert '"source_root"' in output.read_text(encoding="utf-8")
