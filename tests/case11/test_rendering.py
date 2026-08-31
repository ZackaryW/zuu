from __future__ import annotations

from io import StringIO

import pytest

from zuu.case11.state import Action, CheckboxState
from zuu.case11.terminal import AnsiRenderer, CLEAR_LINE


def test_renderer_draws_highlight_checks_and_instruction() -> None:
    stream = StringIO()
    renderer = AnsiRenderer(stream, "Configure agents", ("Codex", "Pi"), columns=200)
    state = CheckboxState(2, selected={0})

    renderer.render(state)

    assert stream.getvalue() == (
        f"{CLEAR_LINE}? Configure agents (Use arrow keys to move, <space> to select, "
        "<a> to toggle, <i> to invert)\n"
        f"{CLEAR_LINE}» ◉ Codex\n"
        f"{CLEAR_LINE}  ○ Pi\n"
        f"{CLEAR_LINE}\n"
    )
    assert renderer.height == 4


def test_renderer_repaints_owned_lines_instead_of_appending_visually() -> None:
    stream = StringIO()
    renderer = AnsiRenderer(stream, "Choose", ("One", "Two"), columns=200)
    state = CheckboxState(2)
    renderer.render(state)

    state.apply(Action.DOWN)
    state.apply(Action.TOGGLE)
    renderer.render(state)

    second_frame = stream.getvalue().split("\x1b[4A", 1)[1]
    assert second_frame.startswith(f"{CLEAR_LINE}? Choose")
    assert f"{CLEAR_LINE}  ○ One\n" in second_frame
    assert f"{CLEAR_LINE}» ◉ Two\n" in second_frame


def test_renderer_repaints_every_physical_row_of_a_wrapped_prompt() -> None:
    stream = StringIO()
    renderer = AnsiRenderer(
        stream,
        "Select agent integrations",
        ("Claude", "Codex", "Kimi", "Pi"),
        columns=100,
    )
    state = CheckboxState(4)
    renderer.render(state)

    assert renderer.height == 7
    assert stream.getvalue().count("\n") == 7

    state.apply(Action.DOWN)
    first_frame_length = len(stream.getvalue())
    renderer.render(state)

    second_frame = stream.getvalue()[first_frame_length:]
    assert second_frame.startswith("\x1b[7A")
    assert second_frame.count("\n") == 7


def test_renderer_shows_and_clears_required_validation() -> None:
    stream = StringIO()
    renderer = AnsiRenderer(stream, "Choose", ("One",), columns=200)
    state = CheckboxState(1, required=True)

    state.apply(Action.SUBMIT)
    renderer.render(state)
    assert "! one or more choices are required" in stream.getvalue()

    state.apply(Action.TOGGLE)
    renderer.render(state)
    assert stream.getvalue().endswith(f"{CLEAR_LINE}\n")


@pytest.mark.parametrize(
    ("selected", "cancelled", "answer"),
    [
        (set(), False, "done"),
        ({0}, False, "[One]"),
        ({0, 1}, False, "done (2 selections)"),
        (set(), True, "cancelled"),
    ],
)
def test_finish_collapses_to_one_outcome_line(
    selected: set[int], cancelled: bool, answer: str
) -> None:
    stream = StringIO()
    renderer = AnsiRenderer(stream, "Choose", ("One", "Two"), columns=200)
    state = CheckboxState(2, selected=selected)
    renderer.render(state)
    state.done = True
    state.cancelled = cancelled

    renderer.finish(state)

    assert f"\x1b[4A{CLEAR_LINE}? Choose {answer}\n" in stream.getvalue()
    with pytest.raises(RuntimeError, match="finished checklist"):
        renderer.render(state)
