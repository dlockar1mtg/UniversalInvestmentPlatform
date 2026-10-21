import json

import pytest

from foundation.production.free_staging import describe_failure, logged_handler


def test_failure_line_names_the_job_and_error():
    line = describe_failure("provider_check", RuntimeError("Alpha Vantage returned no quote"))
    assert line == {"job_failed": "provider_check", "error": "RuntimeError: Alpha Vantage returned no quote"}


def test_secret_values_and_query_keys_are_blanked():
    exc = ValueError("GET https://example.test/q?function=QUOTE&apikey=SYNTHKEY123&symbol=SPY failed; token SYNTHTOKEN99")
    error = describe_failure("provider_check", exc, secrets=["SYNTHTOKEN99", ""])["error"]
    assert "SYNTHKEY123" not in error and "SYNTHTOKEN99" not in error
    assert "apikey=***" in error and "symbol=SPY" in error


def test_short_or_empty_secrets_do_not_blank_ordinary_words():
    error = describe_failure("x", ValueError("bad row"), secrets=["a", "row"])["error"]
    assert error == "ValueError: bad row"


def test_long_errors_are_trimmed_to_one_line():
    error = describe_failure("x", ValueError("line one\n" + "y" * 1000))["error"]
    assert "\n" not in error and len(error) == 300


def test_logged_handler_prints_then_reraises():
    lines = []

    def boom(job):
        raise KeyError("missing")

    with pytest.raises(KeyError):
        logged_handler("net_worth_snapshot", boom, emit=lines.append)(object())
    assert json.loads(lines[0])["job_failed"] == "net_worth_snapshot"


def test_logged_handler_passes_success_through():
    lines = []
    assert logged_handler("x", lambda job: 7, emit=lines.append)(object()) == 7
    assert lines == []
