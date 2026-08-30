from __future__ import annotations

import pytest

from zuu.case11.state import Action, CheckboxState


def test_state_requires_choices() -> None:
    with pytest.raises(ValueError, match="one or more choices"):
        CheckboxState(0)


def test_navigation_wraps_in_both_directions() -> None:
    state = CheckboxState(3)

    state.apply(Action.UP)
    assert state.pointed == 2
    state.apply(Action.DOWN)
    assert state.pointed == 0


def test_toggle_uses_current_pointer() -> None:
    state = CheckboxState(3)

    state.apply(Action.DOWN)
    state.apply(Action.TOGGLE)
    assert state.selected_indexes == (1,)
    state.apply(Action.TOGGLE)
    assert state.selected_indexes == ()


def test_toggle_all_selects_then_clears_every_choice() -> None:
    state = CheckboxState(3, selected={1})

    state.apply(Action.TOGGLE_ALL)
    assert state.selected_indexes == (0, 1, 2)
    state.apply(Action.TOGGLE_ALL)
    assert state.selected_indexes == ()


def test_invert_preserves_declaration_order() -> None:
    state = CheckboxState(4, selected={0, 2})

    state.apply(Action.INVERT)

    assert state.selected_indexes == (1, 3)


def test_optional_empty_submission_completes() -> None:
    state = CheckboxState(2)

    state.apply(Action.SUBMIT)

    assert state.done is True
    assert state.cancelled is False
    assert state.error is None


def test_required_empty_submission_stays_active_until_corrected() -> None:
    state = CheckboxState(2, required=True)

    state.apply(Action.SUBMIT)
    assert state.done is False
    assert state.error == "one or more choices are required"

    state.apply(Action.TOGGLE)
    state.apply(Action.SUBMIT)
    assert state.done is True
    assert state.selected_indexes == (0,)


def test_cancellation_is_distinct_and_discards_checked_values() -> None:
    state = CheckboxState(2, selected={1})

    state.apply(Action.CANCEL)

    assert state.done is True
    assert state.cancelled is True
    assert state.selected_indexes == ()


@pytest.mark.parametrize("action", list(Action))
def test_completed_state_ignores_further_actions(action: Action) -> None:
    state = CheckboxState(2)
    state.apply(Action.SUBMIT)

    state.apply(action)

    assert state.done is True
    assert state.cancelled is False
    assert state.pointed == 0
    assert state.selected_indexes == ()
