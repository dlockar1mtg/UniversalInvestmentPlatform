from scripts.summarize_profile import summarise


def test_inclusive_and_leaf_shares_skip_library_frames():
    lines = [
        "main (/w/scripts/p.py:3);run (/w/foundation/a.py:10);read (/usr/lib/python3.14/socket.py:1);execute (/x/site-packages/psycopg/cursor.py:5) 30",
        "main (/w/scripts/p.py:3);build (/w/foundation/b.py:2);concat (/x/site-packages/pandas/core.py:9) 10",
        "garbage line",
    ]
    total, inc, leaf = summarise(lines)
    assert total == 40
    shares = dict(inc)
    assert shares["main (/w/scripts/p.py)"] == 40 and shares["run (/w/foundation/a.py)"] == 30
    assert not any("pandas" in name or "socket" in name for name in shares)
    assert dict(leaf)["execute (psycopg/cursor.py)"] == 30 and dict(leaf)["build (/w/foundation/b.py)"] == 10
