"""Windows console key translation and transactional mode ownership."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TextIO

from . import TerminalUnavailableError
from .state import Action
from .terminal import HIDE_CURSOR, SHOW_CURSOR

ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004


def translate_windows_key(first: str, continuation: str | None = None) -> Action | None:
    """Translate one Windows console key sequence into a checkbox action."""
    if first in {"\x00", "\xe0"}:
        return {"H": Action.UP, "P": Action.DOWN}.get(continuation or "")
    return {
        " ": Action.TOGGLE,
        "a": Action.TOGGLE_ALL,
        "A": Action.TOGGLE_ALL,
        "i": Action.INVERT,
        "I": Action.INVERT,
        "\r": Action.SUBMIT,
        "\n": Action.SUBMIT,
        "\x03": Action.CANCEL,
        "\x11": Action.CANCEL,
    }.get(first)


class WindowsKeyReader:
    """Read immediate Windows console keys through an injectable character reader."""

    def __init__(self, read_character: Callable[[], str] | None = None) -> None:
        if read_character is None:
            try:
                import msvcrt
            except ImportError as error:
                raise TerminalUnavailableError("Windows console input is unavailable") from error
            read_character = msvcrt.getwch
        self._read_character = read_character

    def read_action(self) -> Action | None:
        """Read and translate one key, consuming extended-key continuations."""
        first = self._read_character()
        continuation = self._read_character() if first in {"\x00", "\xe0"} else None
        return translate_windows_key(first, continuation)


class ConsoleApi(Protocol):
    """Minimum replaceable Windows console-mode boundary."""

    def get_mode(self, stream: TextIO) -> tuple[int, int]: ...

    def set_mode(self, handle: int, mode: int) -> None: ...


class WindowsConsoleApi:
    """Access Windows console modes through standard-library ctypes and msvcrt."""

    def __init__(self) -> None:
        try:
            import ctypes
            import msvcrt
            from ctypes import wintypes
        except ImportError as error:
            raise TerminalUnavailableError("Windows console APIs are unavailable") from error
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetConsoleMode.restype = wintypes.BOOL
        kernel32.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.SetConsoleMode.restype = wintypes.BOOL
        self._ctypes = ctypes
        self._wintypes = wintypes
        self._msvcrt = msvcrt
        self._kernel32 = kernel32

    def get_mode(self, stream: TextIO) -> tuple[int, int]:
        try:
            handle = self._msvcrt.get_osfhandle(stream.fileno())
        except (AttributeError, OSError, ValueError) as error:
            raise TerminalUnavailableError("stream has no Windows console handle") from error
        mode = self._wintypes.DWORD()
        if not self._kernel32.GetConsoleMode(handle, self._ctypes.byref(mode)):
            raise self._ctypes.WinError(self._ctypes.get_last_error())
        return handle, int(mode.value)

    def set_mode(self, handle: int, mode: int) -> None:
        if not self._kernel32.SetConsoleMode(handle, mode):
            raise self._ctypes.WinError(self._ctypes.get_last_error())


class WindowsTerminalSession:
    """Own Windows console modes and cursor visibility for one checklist."""

    def __init__(
        self,
        input_stream: TextIO,
        output_stream: TextIO,
        *,
        console: ConsoleApi | None = None,
        reader: WindowsKeyReader | None = None,
    ) -> None:
        self._input = input_stream
        self._output = output_stream
        self._console = console
        self._reader = reader
        self._input_mode: tuple[int, int] | None = None
        self._output_mode: tuple[int, int] | None = None
        self._cursor_hidden = False
        self._output_changed = False

    def __enter__(self) -> WindowsTerminalSession:
        if not (_is_tty(self._input) and _is_tty(self._output)):
            raise TerminalUnavailableError("interactive input and output terminals are required")
        try:
            console = self._console if self._console is not None else WindowsConsoleApi()
            self._console = console
            self._input_mode = console.get_mode(self._input)
            self._output_mode = console.get_mode(self._output)
            console.set_mode(
                self._output_mode[0],
                self._output_mode[1] | ENABLE_VIRTUAL_TERMINAL_PROCESSING,
            )
            self._output_changed = True
            self._reader = self._reader if self._reader is not None else WindowsKeyReader()
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
        """Read one semantic action from the active Windows console."""
        if self._reader is None:
            raise RuntimeError("Windows terminal session is not active")
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
        if self._console is not None and self._output_mode is not None and self._output_changed:
            try:
                self._console.set_mode(*self._output_mode)
            except BaseException as error:
                errors.append(error)
            self._output_changed = False
        if self._console is not None and self._input_mode is not None:
            try:
                self._console.set_mode(*self._input_mode)
            except BaseException as error:
                errors.append(error)
            self._input_mode = None
        if errors:
            if original is not None:
                original.add_note(f"terminal restoration also failed: {errors[0]}")
            else:
                raise TerminalUnavailableError("Windows terminal restoration failed") from errors[0]


def _is_tty(stream: TextIO) -> bool:
    try:
        return bool(stream.isatty())
    except (AttributeError, OSError, ValueError):
        return False
