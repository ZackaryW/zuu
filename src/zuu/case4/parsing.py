"""Recognition of ordinary single-line Markdown pipe tables."""

import re


SEPARATOR = re.compile(r"^:?-{3,}:?$")


def _cells(line: str) -> tuple[str, ...] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    cells = re.split(r"(?<!\\)\|", stripped[1:-1])
    return tuple(cell.strip().replace("\\|", "|") for cell in cells)


def extract_tables(
    document: str,
) -> tuple[tuple[tuple[str, ...], tuple[tuple[str, ...], ...], int, int], ...]:
    """Return headings, rows, and character spans for recognized tables."""
    lines = document.splitlines(keepends=True)
    offsets: list[int] = []
    position = 0
    for line in lines:
        offsets.append(position)
        position += len(line)

    tables = []
    index = 0
    while index + 1 < len(lines):
        headings = _cells(lines[index])
        separator = _cells(lines[index + 1])
        if not headings or not separator or len(headings) != len(separator):
            index += 1
            continue
        if not all(SEPARATOR.fullmatch(cell) for cell in separator):
            index += 1
            continue

        end = index + 2
        rows = []
        while end < len(lines):
            row = _cells(lines[end])
            if row is None or len(row) != len(headings):
                break
            rows.append(row)
            end += 1

        span_end = offsets[end] if end < len(lines) else len(document)
        tables.append((headings, tuple(rows), offsets[index], span_end))
        index = end
    return tuple(tables)
