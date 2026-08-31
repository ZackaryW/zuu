"""ANSI rendering and interactive checkbox orchestration."""

from __future__ import annotations

import os
import sys
import unicodedata
from typing import TextIO

from . import TerminalUnavailableError
from .state import Action, CheckboxState

HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
CLEAR_LINE = "\r\x1b[2K"


class AnsiRenderer:
    """Repaint one checklist using explicitly wrapped ANSI-cleared rows."""

    def __init__(
        self,
        stream: TextIO,
        message: str,
        labels: tuple[str, ...],
        *,
        columns: int | None = None,
    ) -> None:
        self._stream = stream
        self._message = message
        self._labels = labels
        self._logical_height = len(labels) + 2
        self._columns = columns if columns is not None else _terminal_columns(stream)
        if self._columns < 2:
            raise ValueError("renderer requires a terminal at least two columns wide")
        self._painted_height = 0
        self._painted = False
        self._finished = False

    @property
    def height(self) -> int:
        """Return the number of physical terminal rows currently owned."""
        return self._painted_height or self._logical_height

    def render(self, state: CheckboxState) -> None:
        """Draw the current question, choices, and validation message."""
        if self._finished:
            raise RuntimeError("cannot render a finished checklist")
        instruction = (
            "(Use arrow keys to move, <space> to select, "
            "<a> to toggle, <i> to invert)"
        )
        lines = [f"? {self._message} {instruction}"]
        lines.extend(
            f"{'»' if index == state.pointed else ' '} "
            f"{'◉' if index in state.selected else '○'} {label}"
            for index, label in enumerate(self._labels)
        )
        lines.append(f"! {state.error}" if state.error else "")
        self._paint(lines)

    def finish(self, state: CheckboxState) -> None:
        """Collapse the active checklist to a stable one-line outcome."""
        if self._finished:
            return
        if state.cancelled:
            answer = "cancelled"
        elif not state.selected:
            answer = "done"
        elif len(state.selected) == 1:
            answer = f"[{self._labels[state.selected_indexes[0]]}]"
        else:
            answer = f"done ({len(state.selected)} selections)"
        self._paint([f"? {self._message} {answer}"])
        self._finished = True

    def _paint(self, lines: list[str]) -> None:
        # Leave the last cell unused so consoles cannot defer a soft wrap there.
        rows = [
            row
            for line in lines
            for row in _wrap_terminal_line(line, self._columns - 1)
        ]
        height = max(len(rows), self._painted_height)
        if self._painted:
            self._stream.write(f"\x1b[{self._painted_height}A")
        rows.extend("" for _ in range(height - len(rows)))
        for row in rows:
            self._stream.write(f"{CLEAR_LINE}{row}\n")
        self._stream.flush()
        self._painted_height = height
        self._painted = True


def _terminal_columns(stream: TextIO) -> int:
    try:
        return os.get_terminal_size(stream.fileno()).columns
    except (AttributeError, OSError, ValueError):
        return 80


def _wrap_terminal_line(line: str, columns: int) -> tuple[str, ...]:
    if not line:
        return ("",)
    rows: list[str] = []
    characters: list[str] = []
    width = 0
    for character in line:
        character_width = _terminal_cell_width(character)
        if characters and width + character_width > columns:
            rows.append("".join(characters))
            characters = []
            width = 0
        characters.append(character)
        width += character_width
    rows.append("".join(characters))
    return tuple(rows)


def _terminal_cell_width(character: str) -> int:
    if unicodedata.combining(character):
        return 0
    if unicodedata.east_asian_width(character) in {"F", "W"}:
        return 2
    return 1


def run_checkbox(
    message: str,
    labels: tuple[str, ...],
    *,
    required: bool,
    input_stream: TextIO,
    output_stream: TextIO,
) -> tuple[tuple[int, ...], bool]:
    """Run a supported terminal checklist and return indexes plus cancellation."""
    state = CheckboxState(len(labels), required=required)
    renderer = AnsiRenderer(output_stream, message, labels)
    session = _make_session(input_stream, output_stream)
    with session:
        renderer.render(state)
        while not state.done:
            try:
                action = session.read_action()
            except KeyboardInterrupt:
                action = Action.CANCEL
            if action is None:
                continue
            state.apply(action)
            if state.done:
                renderer.finish(state)
            else:
                renderer.render(state)
    return state.selected_indexes, state.cancelled


def _make_session(input_stream: TextIO, output_stream: TextIO):
    if sys.platform == "win32":
        from .windows import WindowsTerminalSession

        return WindowsTerminalSession(input_stream, output_stream)
    if os.name == "posix":
        from .posix import PosixTerminalSession

        return PosixTerminalSession(input_stream, output_stream)
    raise TerminalUnavailableError(f"unsupported terminal platform: {sys.platform}")
