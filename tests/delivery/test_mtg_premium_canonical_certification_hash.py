from pathlib import Path

from foundation.presentation.mtg_premium_projection import canonical_crlf_sha256


def test_canonical_hash_is_line_ending_portable(tmp_path: Path) -> None:
    lf = tmp_path / "lf.csv"
    crlf = tmp_path / "crlf.csv"

    lf.write_bytes(b"a,b\n1,2\n")
    crlf.write_bytes(b"a,b\r\n1,2\r\n")

    assert canonical_crlf_sha256(lf) == canonical_crlf_sha256(crlf)


def test_canonical_hash_still_detects_content_change(tmp_path: Path) -> None:
    original = tmp_path / "original.csv"
    changed = tmp_path / "changed.csv"

    original.write_bytes(b"a,b\n1,2\n")
    changed.write_bytes(b"a,b\n1,3\n")

    assert canonical_crlf_sha256(original) != canonical_crlf_sha256(changed)
