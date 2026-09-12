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
        lines: int | None = None,
    ) -> None:
        self._stream = stream
        self._message = message
        self._labels = labels
        self._logical_height = len(labels) + 2
        self._fixed_columns = columns
        self._fixed_lines = lines
        dimensions = _terminal_size(stream)
        self._columns = columns if columns is not None else dimensions.columns
        self._lines = lines if lines is not None else dimensions.lines
        self._painted_height = 0
        self._painted = False
        self._finished = False
        self._window_start = 0

    @property
    def height(self) -> int:
        """Return the number of physical terminal rows currently owned."""
        return self._painted_height or self._logical_height

    def render(self, state: CheckboxState) -> None:
        """Draw the current question, choices, and validation message."""
        if self._finished:
            raise RuntimeError("cannot render a finished checklist")
        self._refresh_dimensions()
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
        rows = [row for line in lines for row in _wrap_terminal_line(line, self._columns - 1)]
        if len(rows) >= self._lines or any(
            sum(_terminal_cell_width(c) for c in label) + 4 >= self._columns
            for label in self._labels
        ):
            rows = self._compact_rows(state)
        self._paint(rows)

    def _refresh_dimensions(self) -> None:
        dimensions = _terminal_size(self._stream)
        columns = self._fixed_columns if self._fixed_columns is not None else dimensions.columns
        lines = self._fixed_lines if self._fixed_lines is not None else dimensions.lines
        if self._painted and (columns < self._columns or lines < self._lines):
            # Shrink can reflow or discard the old origin. Relative cursor-up
            # cannot prove ownership afterward, so do not erase speculative rows.
            raise TerminalUnavailableError(
                "terminal resized smaller; restart selection at the new size"
            )
        if columns < 12 or lines < 6:
            raise TerminalUnavailableError(
                "terminal too small for a checklist (minimum 12 columns, 6 rows)"
            )
        self._columns, self._lines = columns, lines

    def _compact_rows(self, state: CheckboxState) -> list[str]:
        width = self._columns - 1
        # Reserve question, controls, range, validation, and a cursor row.
        count = min(len(self._labels), self._lines - 5)
        self._window_start = max(
            0, min(self._window_start, state.pointed, len(self._labels) - count)
        )
        if state.pointed >= self._window_start + count:
            self._window_start = state.pointed - count + 1
        stop = self._window_start + count
        rows = [
            _fit_text(f"? {self._message}", width),
            _fit_text("↑↓ Space a i Enter ^Q", width),
        ]
        rows.extend(
            _fit_text(
                f"{'»' if index == state.pointed else ' '} "
                f"{'◉' if index in state.selected else '○'} {self._labels[index]}", width
            )
            for index in range(self._window_start, stop)
        )
        rows.append(_fit_text(f"{self._window_start + 1}-{stop}/{len(self._labels)}", width))
        rows.append(_fit_text(f"! {state.error}", width) if state.error else "")
        return rows

    def finish(self, state: CheckboxState) -> None:
        """Collapse the active checklist to a stable one-line outcome."""
        if self._finished:
            return
        self._refresh_dimensions()
        if state.cancelled:
            answer = "cancelled"
        elif not state.selected:
            answer = "done"
        elif len(state.selected) == 1:
            answer = f"[{self._labels[state.selected_indexes[0]]}]"
        else:
            answer = f"done ({len(state.selected)} selections)"
        width = self._columns - 1
        answer = _fit_text(answer, max(1, width - 2))
        remaining = width - sum(_terminal_cell_width(c) for c in answer) - 3
        question = _fit_text(self._message, remaining) if remaining > 0 else ""
        self._paint([f"? {question} {answer}" if question else f"? {answer}"])
        self._finished = True

    def _paint(self, lines: list[str]) -> None:
        # Leave the last cell unused so consoles cannot defer a soft wrap there.
        rows = [
            row
            for line in lines
            for row in _wrap_terminal_line(line, self._columns - 1)
        ]
        active_height = len(rows)
        height = max(active_height, self._painted_height)
        if self._painted:
            self._stream.write(f"\x1b[{self._painted_height}A")
        rows.extend("" for _ in range(height - len(rows)))
        for row in rows:
            self._stream.write(f"{CLEAR_LINE}{row}\n")
        if height > active_height:
            self._stream.write(f"\x1b[{height - active_height}A")
        self._stream.flush()
        self._painted_height = active_height
        self._painted = True


def _terminal_size(stream: TextIO) -> os.terminal_size:
    try:
        return os.get_terminal_size(stream.fileno())
    except (AttributeError, OSError, ValueError):
        return os.terminal_size((80, 24))


def _fit_text(text: str, columns: int) -> str:
    if sum(_terminal_cell_width(c) for c in text) <= columns:
        return text
    result = []
    used = 0
    for character in text:
        width = _terminal_cell_width(character)
        if used + width > columns - 1:
            break
        result.append(character)
        used += width
    return "".join(result) + "…"


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
