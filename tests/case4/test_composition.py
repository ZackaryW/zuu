from dataclasses import dataclass

import pytest

from zuu.case4 import Column, MarkdownTable


@dataclass(frozen=True)
class Package:
    name: str
    purpose: str


def test_compose_applies_every_column_to_the_same_source() -> None:
    table = MarkdownTable.compose(
        (
            Column("Package", lambda package: package.name),
            Column("Purpose", lambda package: package.purpose),
        ),
        (Package("case1", "Hash files."), Package("case2", "Capture files.")),
    )

    assert table.headings == ("Package", "Purpose")
    assert table.rows == (
        ("case1", "Hash files."),
        ("case2", "Capture files."),
    )
    assert table.render() == """| Package | Purpose |
|---------|---------|
| case1 | Hash files. |
| case2 | Capture files. |"""


def test_table_rejects_inconsistent_rows() -> None:
    with pytest.raises(ValueError, match="heading count"):
        MarkdownTable(("One", "Two"), (("only one",),))


def test_columns_and_tables_require_unambiguous_headings() -> None:
    with pytest.raises(ValueError, match="column heading"):
        Column("", str)
    with pytest.raises(ValueError, match="non-empty headings"):
        MarkdownTable(())
    with pytest.raises(ValueError, match="non-empty headings"):
        MarkdownTable(("",))
    with pytest.raises(ValueError, match="unique"):
        MarkdownTable(("Name", "Name"))


def test_render_escapes_pipes_flattens_newlines_and_supports_no_rows() -> None:
    table = MarkdownTable(("Value",), (("left|right\nnext",),))

    assert table.render() == "| Value |\n|-------|\n| left\\|right next |"
    assert MarkdownTable(("Empty",)).render() == "| Empty |\n|-------|"


def test_compose_supports_generators_and_stringifies_values() -> None:
    columns = (Column("Doubled", lambda value: value * 2),)

    table = MarkdownTable.compose(columns, (value for value in (1, 2)))

    assert table.rows == (("2",), ("4",))
