from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from zuu.case11 import TerminalUnavailableError
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
def test_posix_reader_reports_eof_in_escape_sequences(
    characters: tuple[str, ...],
) -> None:
    values = iter(characters)
    reader = PosixKeyReader(read_character=lambda: next(values, ""))

    with pytest.raises(TerminalUnavailableError, match="input.*closed"):
        reader.read_action()


@pytest.mark.parametrize("reader_type", [PosixKeyReader, WindowsKeyReader])
def test_reader_reports_empty_input(reader_type) -> None:
    reader = reader_type(read_character=lambda: "")
    with pytest.raises(TerminalUnavailableError, match="input.*closed"):
        reader.read_action()


@pytest.mark.parametrize("prefix", [(), ("\x00",), ("\xe0",)])
@pytest.mark.parametrize("end", ["", "\uffff"])
def test_windows_reader_reports_console_loss(prefix, end) -> None:
    characters = iter((*prefix, end))
    reader = WindowsKeyReader(characters.__next__)
    with pytest.raises(TerminalUnavailableError, match="input.*closed"):
        reader.read_action()


def test_posix_pipe_bytes_are_ignored_until_actual_eof() -> None:
    source, target = os.pipe()
    try:
        os.write(target, b"\xc3\xa9 ")
    finally:
        os.close(target)
    try:
        reader = PosixKeyReader(source)
        assert reader.read_action() is None
        assert reader.read_action() is None
        assert reader.read_action() is Action.TOGGLE
        with pytest.raises(TerminalUnavailableError, match="input.*closed"):
            reader.read_action()
    finally:
        os.close(source)


@pytest.mark.parametrize("prefix", [("\x1b",), ("\x1b", "[")])
def test_posix_reader_does_not_wait_for_an_unavailable_escape_continuation(prefix) -> None:
    characters = iter((*prefix, " "))
    readiness = iter((True,) * (len(prefix) - 1) + (False,))
    reader = PosixKeyReader(
        read_character=characters.__next__,
        continuation_ready=readiness.__next__,
    )

    assert reader.read_action() is None
    assert reader.read_action() is Action.TOGGLE


def test_posix_reader_requires_an_input_boundary() -> None:
    with pytest.raises(ValueError, match="file descriptor"):
        PosixKeyReader()


@pytest.mark.skipif(sys.platform != "win32", reason="requires native Windows CRT")
def test_native_windows_reader_reports_lost_console() -> None:
    source = str(Path(__file__).resolve().parents[2] / "src")
    script = f"""
import ctypes
import sys
sys.path.insert(0, {source!r})
from zuu.case11 import TerminalUnavailableError
from zuu.case11.windows import WindowsKeyReader
ctypes.windll.kernel32.FreeConsole()
try:
    WindowsKeyReader().read_action()
except TerminalUnavailableError:
    print("closed")
else:
    raise AssertionError("lost console was ignored")
"""
    result = subprocess.run(
        [sys._base_executable, "-c", script],
        creationflags=subprocess.DETACHED_PROCESS,
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "closed"
