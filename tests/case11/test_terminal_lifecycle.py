from __future__ import annotations

import sys
from io import StringIO

import pytest

from zuu.case11 import Choice, CliSelector
from zuu.case11.state import Action
from zuu.case11 import terminal


class InteractiveStream(StringIO):
    def isatty(self) -> bool:
        return True


class ScriptedSession:
    def __init__(self, actions: tuple[Action | None | BaseException, ...]) -> None:
        self.actions = iter(actions)
        self.entered = False
        self.exited = False
        self.exit_error: BaseException | None = None

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, traceback
        self.exited = True
        self.exit_error = exc

    def read_action(self) -> Action | None:
        action = next(self.actions)
        if isinstance(action, BaseException):
            raise action
        return action


@pytest.fixture
def selector() -> CliSelector[str]:
    return CliSelector(
        "Configure agent applications",
        (
            Choice("Codex", "codex"),
            Choice("Claude Code", "claude"),
            Choice("Pi", "pi"),
            Choice("Kimi", "kimi"),
        ),
    )


def run_script(
    monkeypatch: pytest.MonkeyPatch,
    selector: CliSelector[str],
    actions: tuple[Action | None | BaseException, ...],
    *,
    required: bool = False,
):
    session = ScriptedSession(actions)
    monkeypatch.setattr(terminal, "_make_session", lambda source, destination: session)
    output = InteractiveStream()
    result = selector.select(
        required=required,
        input_stream=InteractiveStream(),
        output_stream=output,
    )
    return result, output.getvalue(), session


def test_zpp_style_interaction_returns_generic_values_in_choice_order(
    monkeypatch: pytest.MonkeyPatch, selector: CliSelector[str]
) -> None:
    result, output, session = run_script(
        monkeypatch,
        selector,
        (
            Action.DOWN,
            Action.TOGGLE,
            Action.DOWN,
            Action.TOGGLE,
            Action.SUBMIT,
        ),
        required=True,
    )

    assert result.values == ("claude", "pi")
    assert result.cancelled is False
    assert "» ◉ Pi" in output
    assert "done (2 selections)" in output
    assert session.entered is True
    assert session.exited is True
    assert session.exit_error is None


def test_required_empty_submission_shows_feedback_then_accepts_choice(
    monkeypatch: pytest.MonkeyPatch, selector: CliSelector[str]
) -> None:
    result, output, _ = run_script(
        monkeypatch,
        selector,
        (Action.SUBMIT, Action.TOGGLE, Action.SUBMIT),
        required=True,
    )

    assert result.values == ("codex",)
    assert "! one or more choices are required" in output


def test_toggle_all_clear_and_invert_are_composable(
    monkeypatch: pytest.MonkeyPatch, selector: CliSelector[str]
) -> None:
    result, _, _ = run_script(
        monkeypatch,
        selector,
        (Action.TOGGLE_ALL, Action.TOGGLE_ALL, Action.INVERT, Action.SUBMIT),
    )

    assert result.values == ("codex", "claude", "pi", "kimi")


@pytest.mark.parametrize("interrupt", [Action.CANCEL, KeyboardInterrupt()])
def test_cancellation_is_returned_after_session_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    selector: CliSelector[str],
    interrupt: Action | BaseException,
) -> None:
    result, output, session = run_script(monkeypatch, selector, (interrupt,))

    assert result.values == ()
    assert result.cancelled is True
    assert "cancelled" in output
    assert session.exited is True


def test_input_failure_propagates_after_session_cleanup(
    monkeypatch: pytest.MonkeyPatch, selector: CliSelector[str]
) -> None:
    session = ScriptedSession((RuntimeError("read failed"),))
    monkeypatch.setattr(terminal, "_make_session", lambda source, destination: session)

    with pytest.raises(RuntimeError, match="read failed"):
        selector.select(
            input_stream=InteractiveStream(),
            output_stream=InteractiveStream(),
        )

    assert session.exited is True
    assert isinstance(session.exit_error, RuntimeError)


def test_render_failure_propagates_after_session_cleanup(
    monkeypatch: pytest.MonkeyPatch, selector: CliSelector[str]
) -> None:
    class BrokenOutput(InteractiveStream):
        def write(self, value: str) -> int:
            raise OSError("render failed")

    session = ScriptedSession((Action.SUBMIT,))
    monkeypatch.setattr(terminal, "_make_session", lambda source, destination: session)

    with pytest.raises(OSError, match="render failed"):
        selector.select(
            input_stream=InteractiveStream(),
            output_stream=BrokenOutput(),
        )

    assert session.exited is True
    assert isinstance(session.exit_error, OSError)


def test_case11_does_not_import_source_product_dependencies(
    selector: CliSelector[str],
) -> None:
    selector.select(("codex",))

    assert "agent_router" not in sys.modules
    assert "questionary" not in sys.modules
    assert "prompt_toolkit" not in sys.modules
    assert "typer" not in sys.modules
