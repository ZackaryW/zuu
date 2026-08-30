from types import MappingProxyType

import pytest

from zuu.case10 import TombstoneOverlay, TombstoneOverlayError


def test_bind_hide_and_clear_form_an_immutable_lifecycle() -> None:
    empty = TombstoneOverlay[str, int].empty()
    bound = empty.bind("port", 9000)
    hidden = bound.hide("port")
    cleared = hidden.clear("port")

    assert empty.is_empty
    assert empty.bindings == {} and empty.hidden == frozenset()
    assert bound.bindings == {"port": 9000} and bound.hidden == frozenset()
    assert hidden.bindings == {} and hidden.hidden == frozenset({"port"})
    assert cleared.is_empty


def test_bind_removes_a_tombstone_and_hide_removes_a_binding() -> None:
    hidden = TombstoneOverlay[str, int](hidden=["value"])
    rebound = hidden.bind("value", 2)
    rebound_hidden = rebound.hide("value")

    assert rebound.bindings == {"value": 2}
    assert rebound.hidden == frozenset()
    assert rebound_hidden.bindings == {}
    assert rebound_hidden.hidden == frozenset({"value"})


def test_state_transitions_are_idempotent_by_value() -> None:
    bound = TombstoneOverlay[str, int]().bind("value", 1)
    hidden = TombstoneOverlay[str, int]().hide("value")
    empty = TombstoneOverlay[str, int]()

    assert bound.bind("value", 1) == bound
    assert hidden.hide("value") == hidden
    assert empty.clear("value") == empty


def test_declared_state_is_copied_and_exposed_read_only() -> None:
    bindings = {"value": 1}
    hidden = {"old"}
    overlay = TombstoneOverlay(bindings, hidden)
    bindings["value"] = 2
    hidden.add("later")

    assert isinstance(overlay.bindings, MappingProxyType)
    assert overlay.bindings == {"value": 1}
    assert overlay.hidden == frozenset({"old"})
    with pytest.raises(TypeError):
        overlay.bindings["value"] = 3  # type: ignore[index]


def test_overlapping_bindings_and_tombstones_are_rejected() -> None:
    with pytest.raises(TombstoneOverlayError, match="both bound and hidden"):
        TombstoneOverlay({"value": 1}, ["value"])
