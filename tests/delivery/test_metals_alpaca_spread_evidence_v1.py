from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "rehearse_metals_alpaca_spread_evidence_v1.py"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-alpaca-spread-evidence-v1-rehearsal.yml"


def test_script_uses_exact_tickers_sip_and_session_balanced_method():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'TICKERS = ("GLD", "IAU", "SGOL", "SLV", "SIVR", "PPLT", "CPER", "COPX", "URA", "URNM")' in text
    assert '"feed": "sip"' in text
    assert 'MIN_SESSIONS = 20' in text
    assert 'WINDOW_START = dt_time(15, 50)' in text
    assert 'WINDOW_END = dt_time(16, 0)' in text
    assert 'statistics.median(spreads)' in text
    assert 'statistics.median(row["session_median_relative_spread_bps"] for row in latest_twenty)' in text


def test_script_preserves_fail_closed_boundaries():
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"production_quote_collection_authorized": False' in text
    assert '"preferred_vehicle_ranking_ready": False' in text
    assert '"publication_write_performed": False' in text
    assert '"automatic_execution_authorized": False' in text
    assert '"credentials_persisted": False' in text
    assert 'quotes field missing' in text


def test_workflow_is_manual_only_and_secret_backed():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "secrets.ALPACA_API_KEY_ID" in text
    assert "secrets.ALPACA_API_SECRET_KEY" in text
    assert "REHEARSE_ALPACA_SIP_SPREAD_EVIDENCE_V1" in text
    assert "rehearse_metals_alpaca_spread_evidence_v1.py" in text
