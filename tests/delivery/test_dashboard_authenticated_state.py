from pathlib import Path


def test_authenticated_dashboard_hides_connection_panel_and_prints_cleanly():
    css = (Path(__file__).resolve().parents[2] / "foundation" / "production" / "dashboard_assets" / "dashboard.css").read_text(encoding="utf-8")
    assert "[hidden]{display:none!important}" in css
    assert "@media print" in css and ".auth-panel{display:none!important}" in css
