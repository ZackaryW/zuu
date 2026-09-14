"""Bound resource regressions by input counts, without risking a hang or OOM."""

from io import StringIO
import os

import pytest

from zuu.case11 import TerminalUnavailableError, terminal
from zuu.case11.state import Action, CheckboxState
from zuu.case11.terminal import AnsiRenderer, _fit_text


def test_unchanged_navigation_still_checks_resize(monkeypatch):
    size = os.terminal_size((38, 10))
    monkeypatch.setattr(terminal, "_terminal_size", lambda _: size)
    output = StringIO()
    renderer = AnsiRenderer(output, "Choose", ("One",))
    state = CheckboxState(1)
    renderer.render(state)
    length = output.tell()
    state.apply(Action.DOWN)
    renderer.render(state)
    assert output.tell() == length

    size = os.terminal_size((200, 30))
    renderer.render(state)
    assert output.tell() > length
    length = output.tell()
    size = os.terminal_size((38, 10))
    with pytest.raises(TerminalUnavailableError, match="resized"):
        renderer.render(state)
    assert output.tell() == length


@pytest.mark.parametrize("case", ["many_choices", "long_label", "long_message"])
def test_constrained_layout_only_measures_visible_content(monkeypatch, case):
    message = "Q" * 1_000_000 if case == "long_message" else "Choose"
    if case == "many_choices":
        labels = tuple(f"choice-{index}" for index in range(10_000))
    elif case == "long_label":
        labels = ("X" * 1_000_000,)
    else:
        labels = ("One",)
    output = StringIO()
    renderer = AnsiRenderer(output, message, labels, columns=38, lines=10)
    measure = terminal._terminal_cell_width
    calls = 0

    def bounded_measure(character):
        nonlocal calls
        calls += 1
        assert calls <= 5000, "layout scanned beyond the viewport budget"
        return measure(character)

    monkeypatch.setattr(terminal, "_terminal_cell_width", bounded_measure)
    state = CheckboxState(len(labels), pointed=len(labels) - 1)
    renderer.render(state)
    assert renderer.height < 10
    assert len(output.getvalue()) < 500
    if case == "many_choices":
        assert "» ○ choice-9999" in output.getvalue()
    else:
        assert "…" in output.getvalue()
    state.apply(Action.TOGGLE)
    state.apply(Action.SUBMIT)
    renderer.finish(state)
    assert state.selected_indexes == (len(labels) - 1,)


@pytest.mark.parametrize(
    "text,width,expected",
    [
        ("", 3, ""),
        ("abc", 3, "abc"),
        ("abcd", 3, "ab…"),
        ("界a", 3, "界a"),
        ("界界", 3, "界…"),
        ("界", 1, "…"),
        ("e\u0301x", 2, "e\u0301x"),
        ("ae\u0301xy", 3, "ae\u0301…"),
        ("ae\u0301x", 2, "a…"),
    ],
)
def test_text_fitting_preserves_cells_and_combining_marks(text, width, expected):
    assert _fit_text(text, width) == expected
