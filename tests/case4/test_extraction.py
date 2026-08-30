import pytest

from zuu.case4 import MarkdownTable, MarkdownTableError


def test_find_all_extracts_tables_and_unescapes_pipes() -> None:
    document = """# Report

| Name | Note |
|------|------|
| alpha | left \\| right |

Text.

| Key |
|-----|
| value |
"""

    tables = MarkdownTable.find_all(document)

    assert len(tables) == 2
    assert tables[0].headings == ("Name", "Note")
    assert tables[0].rows == (("alpha", "left | right"),)
    assert tables[0].records == ({"Name": "alpha", "Note": "left | right"},)
    assert tables[1].rows == (("value",),)


def test_find_requires_one_exact_heading_match() -> None:
    document = """| Name |
|------|
| first |

| Name |
|------|
| second |
"""

    with pytest.raises(MarkdownTableError, match="found 2"):
        MarkdownTable.find(document, ("Name",))

    with pytest.raises(MarkdownTableError, match="found 0"):
        MarkdownTable.find(document, ("Missing",))


def test_extraction_accepts_alignment_markers_and_a_table_without_rows() -> None:
    document = "| Left | Right |\n|:-----|------:|\n"

    table = MarkdownTable.find(document, ("Left", "Right"))

    assert table.rows == ()


@pytest.mark.parametrize(
    "document",
    [
        "Name | Value\n-----|------\na | b\n",
        "| Name | Value |\n| --- |\n| a | b |\n",
        "| Name |\n| -- |\n| a |\n",
        "| Name |\n| text |\n| a |\n",
    ],
)
def test_extraction_ignores_unsupported_table_shapes(document: str) -> None:
    assert MarkdownTable.find_all(document) == ()
