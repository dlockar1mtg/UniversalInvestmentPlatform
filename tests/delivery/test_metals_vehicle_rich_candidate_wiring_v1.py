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


def test_rehearsal_script_records_non_authorizations():
    text = (ROOT / "scripts" / "rehearse_rich_publication_candidate.py").read_text(encoding="utf-8")
    assert '"postgres_write_performed": False' in text
    assert '"publication_persisted": False' in text
    assert '"publication_activated": False' in text
    assert '"automatic_schedule_modified": False' in text
    assert '"central_publication_cron_restored": False' in text
