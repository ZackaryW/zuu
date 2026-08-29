# case4: Markdown pipe tables

`case4` finds ordinary Markdown pipe tables, extracts their cells, composes new
tables from reusable column definitions, and replaces a table inside its original
document.

It is intentionally smaller than a complete Markdown parser. A supported table has
one header line, one dash separator line, and zero or more single-line rows:

```markdown
| Name | Purpose |
|------|---------|
| cache | Store values. |
```

## Dependencies

This case is standalone and uses only the Python standard library.

## Compose a table

Every `Column` receives the same source object. This lets one definition derive
different cells from a path, parsed variables, or any other data carried by that
source.

```python
from dataclasses import dataclass

from zuu.case4 import Column, MarkdownTable


@dataclass(frozen=True)
class Package:
    name: str
    purpose: str


definition = (
    Column("Package", lambda package: package.name),
    Column("Purpose", lambda package: package.purpose),
)
table = MarkdownTable.compose(
    definition,
    (Package("case1", "Hash files."), Package("case2", "Capture files.")),
)

print(table.render())
```

The result is deterministic and retains the source order:

```markdown
| Package | Purpose |
|---------|---------|
| case1 | Hash files. |
| case2 | Capture files. |
```

## Find and extract tables

`MarkdownTable.find_all(document)` returns every recognized table.
`MarkdownTable.find(document, headings)` requires exactly one table with those
ordered headings. An extracted table exposes `headings`, positional `rows`, and
`records`, which maps each row by heading:

```python
table = MarkdownTable.find(markdown, ("Package", "Purpose"))
print(table.records[0]["Package"])
```

Pipes inside cells must be escaped as `\|`. Extraction returns the unescaped value,
and rendering escapes pipe characters again. Multiline cells, tables without outer
pipes, and broader CommonMark syntax are outside this case's contract.

## Replace a table

Only a table extracted from a document knows the character range it can replace.
The replacement must have the same ordered headings:

```python
current = MarkdownTable.find(markdown, generated.headings)
updated = current.replace_in(
    markdown,
    generated,
    preserve=lambda row: row["Package"] == "manual",
    exclude=lambda row: row["Package"] == "deprecated",
)
```

Rows accepted by `preserve` are kept before the replacement rows. Rows accepted by
`exclude` are then removed from the combined result, so exclusion takes precedence
over preservation. Text before and after the table, including its line-ending
boundary, remains unchanged.

## Errors

- `MarkdownTableError` is raised when exact lookup finds zero or multiple tables,
  when replacement headings differ, or when a composed table is used as a document
  replacement target.
- `ValueError` is raised for empty or duplicate headings and rows with the wrong
  number of cells.

## Tests

Run the focused suite with:

```powershell
uv run pytest -q tests/case4
```
