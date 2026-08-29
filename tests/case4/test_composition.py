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
