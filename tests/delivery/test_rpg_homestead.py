"""The Homestead (household plan) page and its wiring into the dashboard shell."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "foundation" / "production" / "dashboard_assets"


def _read(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def test_homestead_page_nav_route_and_tab():
    html = _read("dashboard.html")
    assert '<button class="nav-item" data-page="homestead">' in html
    assert '<section id="homestead" class="page"' in html
    assert '<script src="/dashboard/assets/homestead.js" defer></script>' in html
    assert "style=" not in html
    assert '@app.get("/dashboard/assets/homestead.js"' in (ROOT / "foundation/production/http_service.py").read_text()
    script = _read("dashboard.js")
    assert 'homestead:"Household plan"' in script and 'homestead:"The Homestead"' in script
    realm = _read("rpg_realm.js")
    assert '["homestead","The Homestead \\u00b7 Plan",\'data-rpg-page="homestead"\']' in realm
    assert "window.UIPRealm={renderHall,renderInventory,renderVault,renderGuild,state,realmTabs,realmTotals,bindNavigation};" in realm


def test_homestead_reads_and_writes_only_the_household_plan_routes():
    page = _read("homestead.js")
    for path in ('call("/v1/household-plan")', 'post("/v1/household-plan/projection"', 'post("/v1/household-plan",{plan})',
                 'call("/v1/household-plan/import"'):
        assert path in page, path
    for heading in ("The road ahead", "What the down payment could be", "The ledger of months", "The house and the plan",
                    "Bring in the workbook", "How the ranges are made"):
        assert heading in page, heading
    assert 'sessionStorage.getItem("uiip-dashboard-key")' in page
    for forbidden in ("localStorage", "eval(", "new Function", "style=", "console.log"):
        assert forbidden not in page, forbidden
    assert page.isascii()


def test_homestead_roll_forward_matches_the_server_formula():
    page = _read("homestead.js")
    assert "prev.bank_balance+toBank" in page
    assert "prev.retirement_balance*(1+rr)" in page and "prev.investment_balance*(1+ri)" in page


def test_homestead_styles_exist():
    css = _read("rpg_theme.css")
    for selector in (".rpg-home-hero{", ".rpg-home-editor{", ".rpg-action{", ".rpg-home-ledger{", ".rpg-home-tiles{flex:none}"):
        assert selector in css, selector


def test_the_deployed_image_installs_what_the_household_plan_imports():
    # The first staging import failed with a 500: the Docker image (phase_7_3) had no openpyxl.
    lines = (ROOT / "requirements" / "phase_7_3.txt").read_text().splitlines()
    names = {line.split(">")[0].split("<")[0].split("[")[0].strip() for line in lines}
    assert {"openpyxl", "numpy", "pandas", "duckdb"} <= names
    assert "requirements/phase_7_3.txt" in (ROOT / "deployment" / "Dockerfile").read_text()


def test_housing_cards_read_the_v11_out_of_sample_calibration():
    page = _read("homestead.js")
    for text in ("cal.in_sample!==false", "Timing test, out of sample over", "not as a forecast of when prices will rise",
                 'pkg.model_version||"V10"'):
        assert text in page, text
    assert page.isascii()
