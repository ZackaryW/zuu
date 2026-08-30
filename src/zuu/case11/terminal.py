"""ANSI rendering and interactive checkbox orchestration."""

from __future__ import annotations

import os
import sys
from typing import TextIO

from . import TerminalUnavailableError
from .state import Action, CheckboxState

HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
CLEAR_LINE = "\r\x1b[2K"


class AnsiRenderer:
    """Repaint one fixed-height checklist using whole ANSI-cleared lines."""

    def __init__(self, stream: TextIO, message: str, labels: tuple[str, ...]) -> None:
        self._stream = stream
        self._message = message
        self._labels = labels
        self._height = len(labels) + 2
        self._painted = False
        self._finished = False

    @property
    def height(self) -> int:
        """Return the fixed number of terminal lines owned by this renderer."""
        return self._height

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
        self._paint([f"? {self._message} {answer}", *("" for _ in range(self._height - 1))])
        self._finished = True

    def _paint(self, lines: list[str]) -> None:
        if len(lines) != self._height:
            raise ValueError("renderer received an unexpected line count")
        if self._painted:
            self._stream.write(f"\x1b[{self._height}A")
        for line in lines:
            self._stream.write(f"{CLEAR_LINE}{line}\n")
        self._stream.flush()
        self._painted = True


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
