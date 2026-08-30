from __future__ import annotations

from io import StringIO
from types import SimpleNamespace

import pytest

from zuu.case11 import TerminalUnavailableError
from zuu.case11.posix import PosixKeyReader, PosixTerminalSession
from zuu.case11.state import Action
from zuu.case11.terminal import HIDE_CURSOR, SHOW_CURSOR
from zuu.case11.windows import (
    ENABLE_VIRTUAL_TERMINAL_PROCESSING,
    WindowsKeyReader,
    WindowsTerminalSession,
)


class TtyStream(StringIO):
    def __init__(self, value: str = "", *, descriptor: int = 10) -> None:
        super().__init__(value)
        self.descriptor = descriptor

    def isatty(self) -> bool:
        return True

    def fileno(self) -> int:
        return self.descriptor


class FakeConsole:
    def __init__(self) -> None:
        self.modes = {10: 0x01, 11: 0x02}
        self.calls: list[tuple[int, int]] = []
        self.fail_after: int | None = None

    def get_mode(self, stream: TtyStream) -> tuple[int, int]:
        return stream.descriptor, self.modes[stream.descriptor]

    def set_mode(self, handle: int, mode: int) -> None:
        self.calls.append((handle, mode))
        if self.fail_after is not None and len(self.calls) >= self.fail_after:
            raise OSError("console mode failure")


def test_windows_session_enables_vt_and_restores_modes_and_cursor() -> None:
    source = TtyStream(descriptor=10)
    destination = TtyStream(descriptor=11)
    console = FakeConsole()
    reader = WindowsKeyReader(iter((" ",)).__next__)

    with WindowsTerminalSession(source, destination, console=console, reader=reader) as session:
        assert session.read_action() is Action.TOGGLE

    assert console.calls == [
        (11, 0x02 | ENABLE_VIRTUAL_TERMINAL_PROCESSING),
        (11, 0x02),
        (10, 0x01),
    ]
    assert destination.getvalue() == HIDE_CURSOR + SHOW_CURSOR


def test_windows_session_restores_after_body_failure() -> None:
    destination = TtyStream(descriptor=11)
    console = FakeConsole()

    with pytest.raises(RuntimeError, match="body failed"):
        with WindowsTerminalSession(
            TtyStream(descriptor=10),
            destination,
            console=console,
            reader=WindowsKeyReader(lambda: "x"),
        ):
            raise RuntimeError("body failed")

    assert destination.getvalue().endswith(SHOW_CURSOR)
    assert console.calls[-2:] == [(11, 0x02), (10, 0x01)]


def test_windows_restoration_failure_does_not_mask_body_failure() -> None:
    console = FakeConsole()
    console.fail_after = 2

    with pytest.raises(RuntimeError, match="body failed") as caught:
        with WindowsTerminalSession(
            TtyStream(descriptor=10),
            TtyStream(descriptor=11),
            console=console,
            reader=WindowsKeyReader(lambda: "x"),
        ):
            raise RuntimeError("body failed")

    assert any("restoration also failed" in note for note in caught.value.__notes__)


def test_windows_setup_failure_restores_captured_input() -> None:
    console = FakeConsole()
    console.fail_after = 1

    with pytest.raises(OSError, match="console mode failure"):
        with WindowsTerminalSession(
            TtyStream(descriptor=10),
            TtyStream(descriptor=11),
            console=console,
            reader=WindowsKeyReader(lambda: "x"),
        ):
            pass

    assert (10, 0x01) in console.calls


class FakeTermios:
    TCSANOW = 0

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.fail_restore = False

    def tcgetattr(self, descriptor: int) -> list[int]:
        self.calls.append(("get", descriptor))
        return [1, 2, 3]

    def tcsetattr(self, descriptor: int, when: int, attributes: list[int]) -> None:
        self.calls.append(("set", descriptor, when, attributes))
        if self.fail_restore:
            raise OSError("restore failed")


class FakeTty:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []
        self.fail = False

    def setcbreak(self, descriptor: int, when: int) -> None:
        self.calls.append((descriptor, when))
        if self.fail:
            raise OSError("setcbreak failed")


def test_posix_session_sets_cbreak_and_restores_mode_and_cursor() -> None:
    termios = FakeTermios()
    tty = FakeTty()
    destination = TtyStream(descriptor=11)
    reader = PosixKeyReader(read_character=iter(("a",)).__next__)

    with PosixTerminalSession(
        TtyStream(descriptor=10),
        destination,
        termios_module=termios,
        tty_module=tty,
        reader=reader,
        term="xterm",
    ) as session:
        assert session.read_action() is Action.TOGGLE_ALL

    assert tty.calls == [(10, 0)]
    assert termios.calls == [("get", 10), ("set", 10, 0, [1, 2, 3])]
    assert destination.getvalue() == HIDE_CURSOR + SHOW_CURSOR


def test_posix_session_rejects_dumb_terminal_before_output() -> None:
    destination = TtyStream(descriptor=11)

    with pytest.raises(TerminalUnavailableError, match="ANSI"):
        with PosixTerminalSession(
            TtyStream(descriptor=10),
            destination,
            termios_module=FakeTermios(),
            tty_module=FakeTty(),
            term="dumb",
        ):
            pass

    assert destination.getvalue() == ""


def test_posix_setup_failure_restores_mode_before_reraising() -> None:
    termios = FakeTermios()
    tty = FakeTty()
    tty.fail = True

    with pytest.raises(OSError, match="setcbreak failed"):
        with PosixTerminalSession(
            TtyStream(descriptor=10),
            TtyStream(descriptor=11),
            termios_module=termios,
            tty_module=tty,
            term="xterm",
        ):
            pass

    assert termios.calls == [("get", 10), ("set", 10, 0, [1, 2, 3])]


def test_posix_restoration_failure_is_reported_without_body_error() -> None:
    termios = FakeTermios()
    termios.fail_restore = True

    with pytest.raises(TerminalUnavailableError, match="restoration failed"):
        with PosixTerminalSession(
            TtyStream(descriptor=10),
            TtyStream(descriptor=11),
            termios_module=termios,
            tty_module=FakeTty(),
            reader=PosixKeyReader(read_character=lambda: "x"),
            term="xterm",
        ):
            pass


@pytest.mark.parametrize("session_type", ["windows", "posix"])
def test_sessions_reject_noninteractive_streams(session_type: str) -> None:
    source = StringIO()
    destination = StringIO()
    if session_type == "windows":
        session = WindowsTerminalSession(source, destination, console=FakeConsole())
    else:
        session = PosixTerminalSession(
            source,
            destination,
            termios_module=FakeTermios(),
            tty_module=SimpleNamespace(),
            term="xterm",
        )

    with pytest.raises(TerminalUnavailableError, match="interactive"):
        with session:
            pass
