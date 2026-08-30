from zuu.case10 import TombstoneOverlay


def test_apply_inherits_overrides_hides_and_adds_without_mutating_base() -> None:
    base = {"host": "localhost", "port": 80, "legacy": True}
    overlay = TombstoneOverlay(
        {"port": 9000, "secure": True},
        hidden=["legacy"],
    )

    result = overlay.apply(base)

    assert result == {"host": "localhost", "port": 9000, "secure": True}
    assert base == {"host": "localhost", "port": 80, "legacy": True}
    assert overlay.bindings == {"port": 9000, "secure": True}
    assert overlay.hidden == frozenset({"legacy"})


def test_clear_exposes_an_inherited_value_again() -> None:
    base = {"value": "from base"}

    assert TombstoneOverlay(hidden=["value"]).apply(base) == {}
    assert TombstoneOverlay(hidden=["value"]).clear("value").apply(base) == base
    assert TombstoneOverlay({"value": "local"}).clear("value").apply(base) == base


def test_apply_preserves_base_positions_and_appends_new_bindings_in_order() -> None:
    overlay = TombstoneOverlay({"second": 20, "fourth": 4})

    result = overlay.apply({"first": 1, "second": 2, "third": 3})

    assert list(result.items()) == [
        ("first", 1),
        ("second", 20),
        ("third", 3),
        ("fourth", 4),
    ]


def test_empty_overlay_returns_an_independent_copy() -> None:
    base = {"value": [1]}
    result = TombstoneOverlay[str, list[int]]().apply(base)

    assert result == base
    assert result is not base


def test_generic_hashable_keys_and_values_are_supported() -> None:
    overlay = TombstoneOverlay({(1, 2): ["local"]}, hidden=[(2, 3)])

    assert overlay.apply({(1, 2): ["base"], (2, 3): ["hidden"]}) == {
        (1, 2): ["local"]
    }
