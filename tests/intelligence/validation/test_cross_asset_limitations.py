from foundation.intelligence.validation import limitations_for_asset_class


def test_known_asset_class_has_limitations() -> None:
    assert limitations_for_asset_class("mtg")


def test_unknown_asset_class_has_no_default_limitations() -> None:
    assert limitations_for_asset_class("unknown") == ()
