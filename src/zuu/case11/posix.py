"""POSIX key translation and transactional terminal-mode ownership."""

from __future__ import annotations

import os
import select
from collections.abc import Callable
from types import ModuleType
from typing import TextIO

from . import TerminalUnavailableError
from .state import Action
from .terminal import HIDE_CURSOR, SHOW_CURSOR


def translate_posix_sequence(sequence: str) -> Action | None:
    """Translate one POSIX character or ANSI key sequence into a checkbox action."""
    return {
        "\x1b[A": Action.UP,
        "\x1b[B": Action.DOWN,
        " ": Action.TOGGLE,
        "a": Action.TOGGLE_ALL,
        "A": Action.TOGGLE_ALL,
        "i": Action.INVERT,
        "I": Action.INVERT,
        "\r": Action.SUBMIT,
        "\n": Action.SUBMIT,
        "\x03": Action.CANCEL,
        "\x11": Action.CANCEL,
    }.get(sequence)


class PosixKeyReader:
    """Read POSIX bytes through an injectable one-character reader."""

    def __init__(
        self,
        file_descriptor: int | None = None,
        read_character: Callable[[], str] | None = None,
        continuation_ready: Callable[[], bool] | None = None,
    ) -> None:
        if read_character is None:
            if file_descriptor is None:
                raise ValueError("a file descriptor or character reader is required")

            def read_character() -> str:
                data = os.read(file_descriptor, 1)
                return data.decode("ascii", errors="ignore")

            def continuation_ready() -> bool:
                return bool(select.select((file_descriptor,), (), (), 0.05)[0])

        self._read_character = read_character
        self._continuation_ready = continuation_ready

    def read_action(self) -> Action | None:
        """Read one key, consuming at most one three-byte ANSI arrow sequence."""
        first = self._read_character()
        if first != "\x1b":
            return translate_posix_sequence(first)
        if self._continuation_ready is not None and not self._continuation_ready():
            return None
        second = self._read_character()
        if second != "[":
            return None
        if self._continuation_ready is not None and not self._continuation_ready():
            return None
        third = self._read_character()
        return translate_posix_sequence(first + second + third)


class PosixTerminalSession:
    """Own POSIX input mode and cursor visibility for one checklist."""

    def __init__(
        self,
        input_stream: TextIO,
        output_stream: TextIO,
        *,
        termios_module: ModuleType | object | None = None,
        tty_module: ModuleType | object | None = None,
        reader: PosixKeyReader | None = None,
        term: str | None = None,
    ) -> None:
        self._input = input_stream
        self._output = output_stream
        self._termios = termios_module
        self._tty = tty_module
        self._reader = reader
        self._term = os.environ.get("TERM") if term is None else term
        self._file_descriptor: int | None = None
        self._attributes = None
        self._mode_changed = False
        self._cursor_hidden = False

    def __enter__(self) -> PosixTerminalSession:
        if not (_is_tty(self._input) and _is_tty(self._output)):
            raise TerminalUnavailableError("interactive input and output terminals are required")
        if self._term == "dumb":
            raise TerminalUnavailableError("the terminal does not support ANSI repainting")
        try:
            if self._termios is None or self._tty is None:
                try:
                    import termios
                    import tty
                except ImportError as error:
                    raise TerminalUnavailableError("POSIX terminal APIs are unavailable") from error
                self._termios = termios
                self._tty = tty
            self._file_descriptor = self._input.fileno()
            self._attributes = self._termios.tcgetattr(self._file_descriptor)
            self._mode_changed = True
            self._tty.setcbreak(self._file_descriptor, self._termios.TCSANOW)
            self._reader = (
                self._reader
                if self._reader is not None
                else PosixKeyReader(self._file_descriptor)
            )
            self._output.write(HIDE_CURSOR)
            self._cursor_hidden = True
            self._output.flush()
            return self
        except BaseException as error:
            self._restore(error)
            raise

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, traceback
        self._restore(exc)

    def read_action(self) -> Action | None:
        """Read one semantic action from the active POSIX terminal."""
        if self._reader is None:
            raise RuntimeError("POSIX terminal session is not active")
        return self._reader.read_action()

    def _restore(self, original: BaseException | None) -> None:
        errors: list[BaseException] = []
        if self._cursor_hidden:
            try:
                self._output.write(SHOW_CURSOR)
                self._output.flush()
            except BaseException as error:
                errors.append(error)
            self._cursor_hidden = False
        if (
            self._mode_changed
            and self._termios is not None
            and self._file_descriptor is not None
        ):
            try:
                self._termios.tcsetattr(
                    self._file_descriptor,
                    self._termios.TCSANOW,
                    self._attributes,
                )
            except BaseException as error:
                errors.append(error)
            self._mode_changed = False
        if errors:
            if original is not None:
                original.add_note(f"terminal restoration also failed: {errors[0]}")
            else:
                raise TerminalUnavailableError("POSIX terminal restoration failed") from errors[0]


def _is_tty(stream: TextIO) -> bool:
    try:
        return bool(stream.isatty())
    except (AttributeError, OSError, ValueError):
        return False
