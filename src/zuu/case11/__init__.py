"""Generic explicit-or-interactive CLI choice selection."""

from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Generic, TextIO, TypeVar

__purpose__ = (
    "Choose CLI values like a station clerk honoring tickets already in hand "
    "before opening a live terminal checklist."
)
__depends__ = ()

Value = TypeVar("Value")


class SelectionError(ValueError):
    """A choice declaration or requested selection violates the selector contract."""


class TerminalUnavailableError(SelectionError):
    """Interactive selection cannot safely use the supplied terminal streams."""


@dataclass(frozen=True, slots=True)
class Choice(Generic[Value]):
    """Pair one printable terminal label with an application-owned value."""

    label: str
    value: Value

    def __post_init__(self) -> None:
        if (
            not isinstance(self.label, str)
            or not self.label
            or not self.label.isprintable()
            or "\n" in self.label
            or "\r" in self.label
        ):
            raise SelectionError("choice labels must be non-empty printable single lines")


@dataclass(frozen=True, slots=True)
class Selection(Generic[Value]):
    """Hold selected values while distinguishing cancellation from an empty answer."""

    values: tuple[Value, ...]
    cancelled: bool = False

    def __post_init__(self) -> None:
        if self.cancelled and self.values:
            raise SelectionError("a cancelled selection cannot contain values")


@dataclass(frozen=True, slots=True, init=False)
class CliSelector(Generic[Value]):
    """Honor explicit values before falling back to a live terminal checklist."""

    message: str
    choices: tuple[Choice[Value], ...]

    def __init__(self, message: str, choices: Iterable[Choice[Value]]) -> None:
        if (
            not isinstance(message, str)
            or not message
            or not message.isprintable()
            or "\n" in message
            or "\r" in message
        ):
            raise SelectionError("selector messages must be non-empty printable single lines")
        declared = tuple(choices)
        if not declared:
            raise SelectionError("one or more choices are required")
        if any(not isinstance(choice, Choice) for choice in declared):
            raise SelectionError("choices must contain Choice values")
        for position, choice in enumerate(declared):
            if _contains((item.value for item in declared[:position]), choice.value):
                raise SelectionError(f"duplicate choice value: {choice.value!r}")
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "choices", declared)

    def select(
        self,
        explicit: Sequence[Value] = (),
        *,
        required: bool = False,
        input_stream: TextIO | None = None,
        output_stream: TextIO | None = None,
    ) -> Selection[Value]:
        """Resolve explicit values or interactively prompt when terminal use is safe.

        Explicit values are validated and returned without examining either stream.
        When they are absent, optional noninteractive selection returns an empty
        result while required noninteractive selection raises ``SelectionError``.
        """
        values = tuple(explicit)
        if values:
            return Selection(self._normalize_explicit(values))

        source = input_stream if input_stream is not None else sys.stdin
        destination = output_stream if output_stream is not None else sys.stdout
        if not (_is_tty(source) and _is_tty(destination)):
            if required:
                raise SelectionError(
                    "one or more explicit values are required without an interactive terminal"
                )
            return Selection(())

        from .terminal import run_checkbox

        indexes, cancelled = run_checkbox(
            self.message,
            tuple(choice.label for choice in self.choices),
            required=required,
            input_stream=source,
            output_stream=destination,
        )
        if cancelled:
            return Selection((), cancelled=True)
        return Selection(tuple(self.choices[index].value for index in indexes))

    def _normalize_explicit(self, values: Sequence[Value]) -> tuple[Value, ...]:
        selected: list[Value] = []
        for value in values:
            if not _contains((choice.value for choice in self.choices), value):
                raise SelectionError(f"unknown explicit value: {value!r}")
            if not _contains(selected, value):
                selected.append(value)
        return tuple(selected)


def _contains(values: Iterable[object], candidate: object) -> bool:
    return any(value == candidate for value in values)


def _is_tty(stream: TextIO) -> bool:
    try:
        return bool(stream.isatty())
    except (AttributeError, OSError, ValueError):
        return False


__all__ = [
    "CliSelector",
    "Choice",
    "Selection",
    "SelectionError",
    "TerminalUnavailableError",
]
