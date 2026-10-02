from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "rehearse_metals_alpaca_quote_suitability_v1.py"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-alpaca-quote-suitability-v1-rehearsal.yml"


def test_script_targets_exact_required_tickers_and_sip_only():
    text = SCRIPT.read_text(encoding="utf-8")
    # The universe comes from the vehicle registry, not a hard-coded tuple.
    assert 'TICKERS = _registered_tickers()' in text
    assert '"config" / "metals" / "vehicles.json"' in text
    assert '"feed": "sip"' in text
    assert 'MIN_SESSIONS = 20' in text
    assert 'ask < bid' in text
    assert '"provider_certified": False' in text
    assert '"quote_collection_authorized": False' in text
    assert '"preferred_vehicle_ranking_ready": False' in text
    assert '"publication_write_performed": False' in text


def test_rehearsal_uses_secret_credentials_and_never_persists_them():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    assert "secrets.ALPACA_API_KEY_ID" in workflow
    assert "secrets.ALPACA_API_SECRET_KEY" in workflow
    assert "ALPACA_API_KEY_ID" in script
    assert "ALPACA_API_SECRET_KEY" in script
    assert '"credentials_persisted": False' in script
    assert "key_id" not in script.split('evidence = {', 1)[1]
    assert "secret_key" not in script.split('evidence = {', 1)[1]


def test_workflow_is_manual_only_and_requires_exact_confirmation():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "PROVE_ALPACA_SIP_10_TICKER_COVERAGE" in text
    assert "rehearse_metals_alpaca_quote_suitability_v1.py" in text


def test_suitability_proof_does_not_equal_provider_certification():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "provider_suitability_pass" in text
    assert "provider_certified'] is False" in text
    assert "quote_collection_authorized'] is False" in text
    assert "preferred_vehicle_ranking_ready'] is False" in text


def test_market_holiday_null_quotes_are_empty_but_missing_field_stays_fail_closed():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'if "quotes" not in payload:' in text
    assert 'if quotes is None:' in text
    assert 'quotes = []' in text
    assert 'missing quotes field' in text
    assert 'quotes field is not a list or null' in text
