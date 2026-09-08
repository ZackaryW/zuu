from dataclasses import FrozenInstanceError

import pytest

from zuu.case14 import UnsupportedYaml, loads


@pytest.mark.parametrize(
    "raw",
    [
        "[one, two]",
        "{a: 1, b: 2}",
        "&shared",
        "*shared",
        "!custom value",
        "0xFF",
        "0o77",
        ".inf",
        "-.Inf",
        ".NaN",
    ],
)
def test_unsupported_values_leave_siblings_readable(raw) -> None:
    assert loads(f"before: 1\nopaque: {raw}\nafter: 2") == {
        "before": 1,
        "opaque": UnsupportedYaml(raw),
        "after": 2,
    }


def test_multiline_flow_retains_comments_and_ignores_brackets_in_quotes() -> None:
    raw = '["x]", # comment with a }\n  {inner: \'it\'\'s ]\'},\n  "escaped \\" quote",\n]'
    assert loads(f"opaque: {raw}\nafter: true") == {
        "opaque": UnsupportedYaml(raw),
        "after": True,
    }


@pytest.mark.parametrize("header", ["|", "|-", "|+", ">", ">-", "&anchor", "!custom"])
def test_opaque_indented_bodies(header) -> None:
    assert loads(f"a: {header}\n  first: unmatched '\n  - next\nb: 2") == {
        "a": UnsupportedYaml(f"{header}\n  first: unmatched '\n  - next"),
        "b": 2,
    }


def test_opaque_list_values_and_compact_mapping_fields() -> None:
    assert loads("- |\n  text\n- name: a\n  value: >\n    text\n  other: 1\n- end") == [
        UnsupportedYaml("|\n  text"),
        {"name": "a", "value": UnsupportedYaml(">\n    text"), "other": 1},
        "end",
    ]


def test_anchors_and_merges_are_preserved_without_resolution() -> None:
    assert loads("base: &base\n  x: 1\ncopy:\n  <<: *base\n  y: 2") == {
        "base": UnsupportedYaml("&base\n  x: 1"),
        "copy": {"<<": UnsupportedYaml("*base"), "y": 2},
    }


def test_root_unsupported_value_and_immutable_public_wrapper() -> None:
    value = loads("[a, b]")
    assert value == UnsupportedYaml("[a, b]")
    with pytest.raises(FrozenInstanceError):
        value.raw = "changed"


@pytest.mark.parametrize(
    "raw",
    [
        '"first line\n  second # line"',
        "'first '' line\n  second line'",
        r'"\N\x41"',
    ],
)
def test_unsupported_quoted_values_preserve_following_fields(raw) -> None:
    assert loads(f"description: {raw}\nname: example") == {
        "description": UnsupportedYaml(raw),
        "name": "example",
    }


def test_root_multiline_quote_and_flow_comments() -> None:
    assert loads("'first\nsecond'") == UnsupportedYaml("'first\nsecond'")
    assert loads("[a, b] # comment") == UnsupportedYaml("[a, b] # comment")


def test_block_scalar_blank_lines_are_not_discarded() -> None:
    assert loads("description: |+\n  text\n\n\nname: example")[
        "description"
    ] == UnsupportedYaml("|+\n  text\n\n")
