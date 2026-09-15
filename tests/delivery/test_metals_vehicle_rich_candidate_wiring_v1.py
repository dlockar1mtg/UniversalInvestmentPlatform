from pathlib import Path

from foundation.presentation.metals_vehicle_implementation_projection import (
    PREFERRED_LABEL,
    ONLY_LABEL,
    build_metals_vehicle_implementation_records,
)
from scripts.rehearse_rich_publication_candidate import (
    assert_metals_vehicle_implementation_semantics,
)

ROOT = Path(__file__).resolve().parents[2]


def test_rich_candidate_vehicle_semantics_are_exact_and_fail_closed():
    records = build_metals_vehicle_implementation_records(ROOT)
    summary = assert_metals_vehicle_implementation_semantics(records)

    assert summary["metals:commodity:gold"]["order"] == ["GLD", "SGOL", "IAU"]
    assert summary["metals:commodity:gold"]["labels"]["GLD"] == PREFERRED_LABEL

    assert summary["metals:commodity:silver"]["order"] == ["SLV", "SIVR"]
    assert all(
        label != PREFERRED_LABEL
        for label in summary["metals:commodity:silver"]["labels"].values()
    )

    assert summary["metals:commodity:platinum"]["order"] == ["PPLT"]
    assert summary["metals:commodity:platinum"]["labels"]["PPLT"] == ONLY_LABEL

    assert summary["metals:commodity:copper"]["order"] == ["COPX", "CPER"]
    assert summary["metals:commodity:copper"]["labels"]["COPX"] == PREFERRED_LABEL

    assert summary["metals:commodity:uranium"]["order"] == ["URA", "URNM"]
    assert summary["metals:commodity:uranium"]["labels"]["URA"] == PREFERRED_LABEL


def test_rehearsal_script_records_non_authorizations():
    text = (ROOT / "scripts" / "rehearse_rich_publication_candidate.py").read_text(encoding="utf-8")
    assert '"postgres_write_performed": False' in text
    assert '"publication_persisted": False' in text
    assert '"publication_activated": False' in text
    assert '"automatic_schedule_modified": False' in text
    assert '"central_publication_cron_restored": False' in text
