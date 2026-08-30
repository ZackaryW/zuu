from __future__ import annotations

import pytest

from zuu.case11.posix import PosixKeyReader, translate_posix_sequence
from zuu.case11.state import Action
from zuu.case11.windows import WindowsKeyReader, translate_windows_key


@pytest.mark.parametrize(
    ("first", "continuation", "expected"),
    [
        ("\xe0", "H", Action.UP),
        ("\x00", "P", Action.DOWN),
        (" ", None, Action.TOGGLE),
        ("a", None, Action.TOGGLE_ALL),
        ("i", None, Action.INVERT),
        ("\r", None, Action.SUBMIT),
        ("\x03", None, Action.CANCEL),
        ("\x11", None, Action.CANCEL),
        ("x", None, None),
        ("\xe0", "K", None),
    ],
)
def test_windows_key_translation(
    first: str, continuation: str | None, expected: Action | None
) -> None:
    assert translate_windows_key(first, continuation) is expected


def test_windows_reader_consumes_extended_continuation() -> None:
    characters = iter(("\xe0", "P", " "))
    reader = WindowsKeyReader(lambda: next(characters))

    assert reader.read_action() is Action.DOWN
    assert reader.read_action() is Action.TOGGLE


@pytest.mark.parametrize(
    ("sequence", "expected"),
    [
        ("\x1b[A", Action.UP),
        ("\x1b[B", Action.DOWN),
        (" ", Action.TOGGLE),
        ("A", Action.TOGGLE_ALL),
        ("I", Action.INVERT),
        ("\n", Action.SUBMIT),
        ("\x03", Action.CANCEL),
        ("\x11", Action.CANCEL),
        ("x", None),
        ("\x1b[C", None),
    ],
)
def test_posix_key_translation(sequence: str, expected: Action | None) -> None:
    assert translate_posix_sequence(sequence) is expected


def test_posix_reader_consumes_arrow_sequence() -> None:
    characters = iter(("\x1b", "[", "A", "i"))
    reader = PosixKeyReader(read_character=lambda: next(characters, ""))

    assert reader.read_action() is Action.UP
    assert reader.read_action() is Action.INVERT


@pytest.mark.parametrize("characters", [("\x1b", ""), ("\x1b", "[", "")])
def test_posix_reader_ignores_incomplete_escape_sequences(
    characters: tuple[str, ...],
) -> None:
    values = iter(characters)
    reader = PosixKeyReader(read_character=lambda: next(values, ""))

    assert reader.read_action() is None


def test_posix_reader_does_not_wait_for_an_unavailable_escape_continuation() -> None:
    reader = PosixKeyReader(
        read_character=lambda: "\x1b",
        continuation_ready=lambda: False,
    )

    assert reader.read_action() is None


def test_posix_reader_requires_an_input_boundary() -> None:
    with pytest.raises(ValueError, match="file descriptor"):
        PosixKeyReader()
