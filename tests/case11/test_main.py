from __future__ import annotations

import pytest

from zuu.case11 import CliSelector, Selection, TerminalUnavailableError
from zuu.case11.__main__ import main


def test_demo_explicit_values_bypass_interaction_and_deduplicate(capsys) -> None:
    status = main(
        (
            "--agent",
            "codex",
            "--agent",
            "pi",
            "--agent",
            "codex",
        )
    )

    captured = capsys.readouterr()
    assert status == 0
    assert captured.out == "Selected: codex, pi\n"
    assert captured.err == ""


def test_demo_optional_noninteractive_omission_reports_none(capsys) -> None:
    status = main(("--optional",))

    captured = capsys.readouterr()
    assert status == 0
    assert captured.out == "Selected: none\n"


def test_demo_required_noninteractive_omission_reports_error(capsys) -> None:
    status = main(())

    captured = capsys.readouterr()
    assert status == 2
    assert "explicit values are required" in captured.err


def test_demo_delegates_interactive_selection(monkeypatch, capsys) -> None:
    calls: list[tuple[tuple[str, ...], bool]] = []

    def select(self, explicit=(), *, required=False, **kwargs):
        calls.append((tuple(explicit), required))
        return Selection(("claude", "kimi"))

    monkeypatch.setattr(CliSelector, "select", select)

    assert main(()) == 0
    assert calls == [((), True)]
    assert capsys.readouterr().out == "Selected: claude, kimi\n"


def test_demo_reports_cancellation_with_distinct_status(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        CliSelector,
        "select",
        lambda self, explicit=(), **kwargs: Selection((), cancelled=True),
    )

    status = main(())

    captured = capsys.readouterr()
    assert status == 130
    assert captured.err == "Selection cancelled.\n"


def test_demo_reports_terminal_failure(monkeypatch, capsys) -> None:
    def fail(self, explicit=(), **kwargs):
        raise TerminalUnavailableError("console unavailable")

    monkeypatch.setattr(CliSelector, "select", fail)

    status = main(())

    captured = capsys.readouterr()
    assert status == 2
    assert captured.err == "Selection error: console unavailable\n"


def test_demo_rejects_unknown_agent_through_argparse() -> None:
    with pytest.raises(SystemExit) as caught:
        main(("--agent", "unknown"))

    assert caught.value.code == 2
