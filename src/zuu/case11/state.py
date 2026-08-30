"""Pure transition model for a terminal checkbox."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Action(StrEnum):
    """Semantic actions understood by the platform-independent checkbox state."""

    UP = "up"
    DOWN = "down"
    TOGGLE = "toggle"
    TOGGLE_ALL = "toggle_all"
    INVERT = "invert"
    SUBMIT = "submit"
    CANCEL = "cancel"


@dataclass(slots=True)
class CheckboxState:
    """Track focus, checked indexes, validation, and completion without terminal I/O."""

    count: int
    required: bool = False
    pointed: int = 0
    selected: set[int] = field(default_factory=set)
    error: str | None = None
    done: bool = False
    cancelled: bool = False

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("checkbox state requires one or more choices")

    @property
    def selected_indexes(self) -> tuple[int, ...]:
        """Return checked indexes in declaration order."""
        return tuple(index for index in range(self.count) if index in self.selected)

    def apply(self, action: Action) -> None:
        """Apply one semantic action, ignoring further input after completion."""
        if self.done:
            return
        if action is Action.UP:
            self.pointed = (self.pointed - 1) % self.count
            self.error = None
        elif action is Action.DOWN:
            self.pointed = (self.pointed + 1) % self.count
            self.error = None
        elif action is Action.TOGGLE:
            if self.pointed in self.selected:
                self.selected.remove(self.pointed)
            else:
                self.selected.add(self.pointed)
            self.error = None
        elif action is Action.TOGGLE_ALL:
            self.selected = set() if len(self.selected) == self.count else set(range(self.count))
            self.error = None
        elif action is Action.INVERT:
            self.selected = set(range(self.count)) - self.selected
            self.error = None
        elif action is Action.SUBMIT:
            if self.required and not self.selected:
                self.error = "one or more choices are required"
            else:
                self.done = True
                self.error = None
        elif action is Action.CANCEL:
            self.selected.clear()
            self.cancelled = True
            self.done = True
            self.error = None
