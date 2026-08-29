import pytest

from zuu.case4 import MarkdownTable, MarkdownTableError


def test_replace_preserves_selected_manual_rows_and_surrounding_text() -> None:
    document = """Before.

| Case | Purpose |
|------|---------|
| case0 | Manual. |
| case1 | Stale. |

After.
"""
    current = MarkdownTable.find(document, ("Case", "Purpose"))
    generated = MarkdownTable(
        ("Case", "Purpose"),
        (("case1", "Generated."), ("case2", "New.")),
    )

    updated = current.replace_in(
        document,
        generated,
        preserve=lambda row: row["Case"] == "case0",
    )

    assert updated == """Before.

| Case | Purpose |
|------|---------|
| case0 | Manual. |
| case1 | Generated. |
| case2 | New. |

After.
"""


def test_replace_excludes_selected_rows_after_composition() -> None:
    document = """| Case |
|------|
| old |
"""
    current = MarkdownTable.find(document, ("Case",))
    generated = MarkdownTable(
        ("Case",),
        (("case0",), ("case1",)),
    )

    updated = current.replace_in(
        document,
        generated,
        exclude=lambda row: row["Case"] == "case0",
    )

    assert updated == """| Case |
|------|
| case1 |
"""


def test_composed_table_cannot_replace_document_text() -> None:
    table = MarkdownTable(("Case",), (("case1",),))

    with pytest.raises(MarkdownTableError, match="extracted table"):
        table.replace_in("document", table)


def test_replace_preserves_crlf_table_line_endings() -> None:
    document = "| Name |\r\n|------|\r\n| old |\r\n"
    current = MarkdownTable.find(document, ("Name",))

    updated = current.replace_in(document, MarkdownTable(("Name",), (("new",),)))

    assert updated == "| Name |\r\n|------|\r\n| new |\r\n"
