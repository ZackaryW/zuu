from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import zuu.case11 as case11
from zuu.case11 import (
    Choice,
    CliSelector,
    Selection,
    SelectionError,
    TerminalUnavailableError,
)


def test_public_contract_and_metadata() -> None:
    assert case11.__all__[0] == "CliSelector"
    assert case11.__depends__ == ()
    assert "station clerk" in case11.__purpose__
    assert set(case11.__all__) == {
        "CliSelector",
        "Choice",
        "Selection",
        "SelectionError",
        "TerminalUnavailableError",
    }
    assert issubclass(TerminalUnavailableError, SelectionError)


def test_choices_and_selections_are_frozen() -> None:
    choice = Choice("Codex", "codex")
    selection = Selection(("codex",))

    with pytest.raises(FrozenInstanceError):
        choice.label = "Pi"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        selection.cancelled = True  # type: ignore[misc]


@pytest.mark.parametrize("label", ["", "line\nbreak", "return\rbreak", "bell\a"])
def test_choice_rejects_unsafe_labels(label: str) -> None:
    with pytest.raises(SelectionError, match="choice labels"):
        Choice(label, "value")


@pytest.mark.parametrize("message", ["", "line\nbreak", "return\rbreak", "bell\a"])
def test_selector_rejects_unsafe_messages(message: str) -> None:
    with pytest.raises(SelectionError, match="selector messages"):
        CliSelector(message, (Choice("One", 1),))


def test_selector_preserves_ordered_generic_choices() -> None:
    marker = object()
    selector = CliSelector(
        "Choose values",
        (Choice("Mapping", {"name": "value"}), Choice("Marker", marker)),
    )

    assert tuple(choice.label for choice in selector.choices) == ("Mapping", "Marker")
    assert selector.choices[0].value == {"name": "value"}
    assert selector.choices[1].value is marker


def test_selector_rejects_empty_and_non_choice_declarations() -> None:
    with pytest.raises(SelectionError, match="one or more choices"):
        CliSelector("Choose", ())
    with pytest.raises(SelectionError, match="Choice values"):
        CliSelector("Choose", ("not-a-choice",))  # type: ignore[arg-type]


def test_selector_rejects_duplicate_unhashable_values() -> None:
    with pytest.raises(SelectionError, match="duplicate choice value"):
        CliSelector(
            "Choose",
            (Choice("First", [1, 2]), Choice("Again", [1, 2])),
        )


def test_cancelled_selection_cannot_contain_values() -> None:
    with pytest.raises(SelectionError, match="cancelled selection"):
        Selection(("codex",), cancelled=True)
