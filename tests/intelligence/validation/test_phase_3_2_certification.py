from foundation.intelligence.validation import certify_phase_3_2_structure


def test_phase_3_2_structure_is_complete() -> None:
    result = certify_phase_3_2_structure(".")
    assert result.passed is True
    assert result.missing_files == ()
