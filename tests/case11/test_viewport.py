"""Screen outcomes, independent of the renderer's choice of repaint sequences."""

import os
import re
import unicodedata

import pytest

from zuu.case11.state import Action, CheckboxState
from zuu.case11.terminal import AnsiRenderer
from zuu.case11 import TerminalUnavailableError, terminal
from zuu.case11.windows import WindowsTerminalSession


class Screen:
    def __init__(self, columns=38, lines=30):
        self.columns, self.lines = columns, lines
        self.cells = [[" "] * columns for _ in range(lines)]
        self.history = []
        self.row = self.column = 0
        self.visible = True

    def fileno(self):
        return 123

    def isatty(self):
        return True

    def flush(self):
        pass

    def resize(self, columns, lines):
        self.cells = [(row + [" "] * columns)[:columns] for row in self.cells]
        if lines < self.lines:
            removed = self.lines - lines
            self.history.extend("".join(row).rstrip() for row in self.cells[:removed])
            self.cells = self.cells[removed:]
            self.row = max(0, self.row - removed)
        else:
            self.cells.extend([[" "] * columns for _ in range(lines - self.lines)])
        self.column = min(self.column, columns - 1)
        self.columns, self.lines = columns, lines

    def size(self, descriptor):
        assert descriptor == 123
        return os.terminal_size((self.columns, self.lines))

    @property
    def rows(self):
        return ["".join(row).rstrip() for row in self.cells]

    def newline(self):
        self.row += 1
        if self.row == self.lines:
            self.history.append("".join(self.cells.pop(0)).rstrip())
            self.cells.append([" "] * self.columns)
            self.row -= 1

    def write(self, text):
        position = 0
        while position < len(text):
            character = text[position]
            if character == "\x1b":
                match = re.match(r"\x1b\[([?\d]*)([ABKhl])", text[position:])
                assert match, f"unsupported terminal output: {text[position:]!r}"
                argument, operation = match.groups()
                if operation == "A":
                    self.row = max(0, self.row - int(argument or 1))
                elif operation == "B":
                    self.row = min(self.lines - 1, self.row + int(argument or 1))
                elif operation == "K":
                    assert argument == "2"
                    self.cells[self.row] = [" "] * self.columns
                else:
                    assert argument == "?25"
                    self.visible = operation == "h"
                position += len(match[0])
                continue
            if character == "\r":
                self.column = 0
            elif character == "\n":
                self.newline()
            else:
                width = 0 if unicodedata.combining(character) else (
                    2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
                )
                if width == 0:
                    self.cells[self.row][max(0, self.column - 1)] += character
                else:
                    if self.column + width > self.columns:
                        self.column = 0
                        self.newline()
                    self.cells[self.row][self.column] = character
                    if width == 2:
                        self.cells[self.row][self.column + 1] = ""
                    self.column += width
            position += 1
        return len(text)


def test_screen_models_terminal_bounds_and_scrollback():
    screen = Screen(4, 3)
    screen.write("12345\r\nxy\r\n")
    assert screen.history == ["1234"]
    assert screen.rows == ["5", "xy", ""]
    screen.write("\x1b[99A\r\x1b[2K界e\u0301")
    assert screen.rows == ["界e\u0301", "xy", ""]
    screen.write("\x1b[99B\rZ")
    assert (screen.row, screen.column) == (2, 1)


@pytest.mark.parametrize("cancel", [False, True])
def test_consecutive_selectors_collapse_at_bottom(monkeypatch, cancel):
    screen = Screen()
    monkeypatch.setattr(os, "get_terminal_size", screen.size)
    for number in range(26):
        screen.write(f"earlier {number}\r\n")
    first = AnsiRenderer(screen, "Select agents (--agent)", ("codex", "claude", "kimi", "pi"))
    state = CheckboxState(4, required=True)
    first.render(state)
    state.apply(Action.SUBMIT)
    first.render(state)
    state.apply(Action.CANCEL if cancel else Action.TOGGLE)
    if not cancel:
        state.apply(Action.SUBMIT)
    first.finish(state)
    outcome = next(i for i, row in enumerate(screen.rows) if "? Select agents" in row)
    assert screen.row == outcome + 1
    assert all(not row for row in screen.rows[screen.row:])
    second = AnsiRenderer(screen, "Select skills", tuple(f"skill-{i:02}" for i in range(17)))
    second.render(CheckboxState(17))
    combined = screen.history + screen.rows
    assert combined[:26] == [f"earlier {number}" for number in range(26)]
    first_index = next(i for i, row in enumerate(combined) if "? Select agents" in row)
    assert "? Select skills" in combined[first_index + 1]


def test_short_viewport_keeps_focus_and_full_list_selection(monkeypatch):
    screen = Screen(38, 10)
    monkeypatch.setattr(os, "get_terminal_size", screen.size)
    labels = tuple(f"skill-{i:02}" for i in range(17))
    renderer = AnsiRenderer(screen, "Select skills (--name or --all)", labels)
    state = CheckboxState(17)
    renderer.render(state)
    assert screen.history == []
    for index in range(17):
        assert f"» ○ skill-{index:02}" in screen.rows
        assert sum(row.startswith("? ") for row in screen.rows) == 1
        assert any("/17" in row for row in screen.rows)
        state.apply(Action.DOWN)
        renderer.render(state)
        assert screen.history == []
    state.apply(Action.TOGGLE)
    state.apply(Action.UP)
    renderer.render(state)
    assert "» ○ skill-16" in screen.rows
    state.apply(Action.TOGGLE_ALL)
    renderer.render(state)
    assert state.selected_indexes == tuple(range(17))
    assert "» ◉ skill-16" in screen.rows
    state.apply(Action.INVERT)
    renderer.render(state)
    assert state.selected_indexes == ()
    state.apply(Action.TOGGLE)
    state.apply(Action.DOWN)
    state.apply(Action.TOGGLE)
    state.apply(Action.SUBMIT)
    renderer.finish(state)
    assert state.selected_indexes == (0, 16)
    assert screen.row == 1
    assert all(not row for row in screen.rows[1:])


def test_narrow_viewport_fits_wide_labels_and_validation(monkeypatch):
    screen = Screen(24, 8)
    monkeypatch.setattr(os, "get_terminal_size", screen.size)
    renderer = AnsiRenderer(screen, "Choose a framework", ("界e\u0301" * 40, "Second"))
    state = CheckboxState(2, required=True)
    state.apply(Action.SUBMIT)
    renderer.render(state)
    assert screen.history == []
    assert any(row.startswith("» ○ 界e\u0301") and row.endswith("…") for row in screen.rows)
    assert any(row.startswith("! ") for row in screen.rows)
    assert renderer.height < screen.lines
    state.apply(Action.TOGGLE)
    renderer.render(state)
    assert not any(row.startswith("! ") for row in screen.rows)


def test_expansion_refreshes_layout_and_keeps_selection(monkeypatch):
    screen = Screen(38, 10)
    monkeypatch.setattr(os, "get_terminal_size", screen.size)
    renderer = AnsiRenderer(screen, "Choose", tuple(f"skill-{i:02}" for i in range(17)))
    state = CheckboxState(17, pointed=16, selected={0, 16})
    renderer.render(state)
    assert "  ◉ skill-00" not in screen.rows
    screen.resize(100, 30)
    renderer.render(state)
    assert "  ◉ skill-00" in screen.rows
    assert "» ◉ skill-16" in screen.rows
    assert state.selected_indexes == (0, 16)
    assert screen.history == []


@pytest.mark.parametrize("size,finish", [((24, 10), False), ((38, 8), False), ((24, 8), True)])
def test_unsafe_shrink_does_not_erase_unknown_rows(monkeypatch, size, finish):
    screen = Screen(38, 10)
    monkeypatch.setattr(os, "get_terminal_size", screen.size)
    renderer = AnsiRenderer(screen, "Choose", ("One", "Two"))
    state = CheckboxState(2, selected={1})
    renderer.render(state)
    screen.resize(*size)
    before = (screen.rows, list(screen.history), screen.row, screen.column)
    with pytest.raises(TerminalUnavailableError, match="resiz"):
        renderer.finish(state) if finish else renderer.render(state)
    assert (screen.rows, screen.history, screen.row, screen.column) == before
    assert state.selected_indexes == (1,)


@pytest.mark.parametrize("size", [(1, 5), (10, 5), (38, 4)])
def test_unusable_size_fails_before_paint(monkeypatch, size):
    screen = Screen(*size)
    monkeypatch.setattr(os, "get_terminal_size", screen.size)
    renderer = AnsiRenderer(screen, "Pick", ("A",))
    with pytest.raises(TerminalUnavailableError, match="small"):
        renderer.render(CheckboxState(1))
    assert screen.row == 0 and not any(screen.rows)


def test_resize_failure_restores_session_modes_and_cursor(monkeypatch):
    screen = Screen(38, 10)
    monkeypatch.setattr(os, "get_terminal_size", screen.size)

    class Console:
        def __init__(self):
            self.mode = 1

        def get_mode(self, stream):
            return 123, self.mode

        def set_mode(self, handle, mode):
            self.mode = mode

    class Reader:
        read = False

        def read_action(self):
            if self.read:
                return Action.CANCEL
            self.read = True
            screen.resize(20, 8)
            return Action.DOWN

    console = Console()
    monkeypatch.setattr(terminal, "_make_session", lambda source, target: WindowsTerminalSession(
        source, target, console=console, reader=Reader()
    ))
    with pytest.raises(TerminalUnavailableError, match="resiz"):
        terminal.run_checkbox("Pick", ("One", "Two"), required=True,
                              input_stream=screen, output_stream=screen)
    assert screen.visible
    assert console.mode == 1
