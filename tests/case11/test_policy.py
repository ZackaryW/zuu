from __future__ import annotations

from io import StringIO

import pytest

from zuu.case11 import Choice, CliSelector, SelectionError


class ExplodingStream(StringIO):
    def isatty(self) -> bool:
        raise AssertionError("explicit selection must not inspect streams")

    def read(self, *args, **kwargs):
        raise AssertionError("explicit selection must not read streams")

    def write(self, *args, **kwargs):
        raise AssertionError("explicit selection must not write streams")


class NonInteractiveStream(StringIO):
    def isatty(self) -> bool:
        return False


@pytest.fixture
def selector() -> CliSelector[str]:
    return CliSelector(
        "Configure agents",
        (
            Choice("Codex", "codex"),
            Choice("Claude Code", "claude"),
            Choice("Pi", "pi"),
        ),
    )


def test_explicit_values_win_without_touching_streams(selector: CliSelector[str]) -> None:
    stream = ExplodingStream()

    result = selector.select(
        ("codex", "pi", "codex"),
        required=True,
        input_stream=stream,
        output_stream=stream,
    )

    assert result.values == ("codex", "pi")
    assert result.cancelled is False


def test_unknown_explicit_value_fails_without_touching_streams(
    selector: CliSelector[str],
) -> None:
    stream = ExplodingStream()

    with pytest.raises(SelectionError, match="unknown explicit value"):
        selector.select(("unknown",), input_stream=stream, output_stream=stream)


def test_optional_noninteractive_omission_is_empty(selector: CliSelector[str]) -> None:
    result = selector.select(
        input_stream=NonInteractiveStream(),
        output_stream=NonInteractiveStream(),
    )

    assert result.values == ()
    assert result.cancelled is False


def test_required_noninteractive_omission_fails(selector: CliSelector[str]) -> None:
    with pytest.raises(SelectionError, match="explicit values are required"):
        selector.select(
            required=True,
            input_stream=NonInteractiveStream(),
            output_stream=NonInteractiveStream(),
        )


def test_unusable_isatty_is_treated_as_noninteractive(selector: CliSelector[str]) -> None:
    class BrokenTty(StringIO):
        def isatty(self) -> bool:
            raise OSError("detached")

    result = selector.select(input_stream=BrokenTty(), output_stream=BrokenTty())

    assert result.values == ()
