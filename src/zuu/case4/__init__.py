"""Composable Markdown pipe-table models and operations."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Generic, TypeVar

__purpose__ = "Find, extract, compose, and replace Markdown pipe tables."
__depends__ = ()

Source = TypeVar("Source")


class MarkdownTableError(ValueError):
    """A Markdown table cannot be found or represented unambiguously."""


@dataclass(frozen=True, slots=True)
class Column(Generic[Source]):
    """Define one heading and how its cell is derived from a shared source."""

    heading: str
    parse: Callable[[Source], str]

    def __post_init__(self) -> None:
        if not self.heading:
            raise ValueError("column heading must not be empty")


@dataclass(frozen=True, slots=True)
class MarkdownTable:
    """An extracted or composed single-line Markdown pipe table."""

    headings: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...] = ()
    _start: int | None = field(default=None, repr=False, compare=False)
    _end: int | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.headings or any(not heading for heading in self.headings):
            raise ValueError("a Markdown table requires non-empty headings")
        if len(set(self.headings)) != len(self.headings):
            raise ValueError("Markdown table headings must be unique")
        if any(len(row) != len(self.headings) for row in self.rows):
            raise ValueError("every Markdown table row must match the heading count")

    @classmethod
    def find_all(cls, document: str) -> tuple[MarkdownTable, ...]:
        """Extract every ordinary pipe table from a Markdown document."""
        from .parsing import extract_tables

        tables = extract_tables(document)
        return tuple(
            cls(headings, rows, start, end)
            for headings, rows, start, end in tables
        )

    @classmethod
    def find(cls, document: str, headings: Iterable[str]) -> MarkdownTable:
        """Find exactly one table with the supplied ordered headings."""
        expected = tuple(headings)
        matches = [table for table in cls.find_all(document) if table.headings == expected]
        if len(matches) != 1:
            raise MarkdownTableError(
                f"expected one Markdown table with headings {expected!r}; found {len(matches)}"
            )
        return matches[0]

    @classmethod
    def compose(
        cls,
        columns: Iterable[Column[Source]],
        sources: Iterable[Source],
    ) -> MarkdownTable:
        """Compose rows by applying every column to each shared source."""
        definitions = tuple(columns)
        return cls(
            tuple(column.heading for column in definitions),
            tuple(
                tuple(str(column.parse(source)) for column in definitions)
                for source in sources
            ),
        )

    @property
    def records(self) -> tuple[Mapping[str, str], ...]:
        """Expose rows keyed by their headings."""
        return tuple(dict(zip(self.headings, row, strict=True)) for row in self.rows)

    def render(self) -> str:
        """Render the table using deterministic spacing and escaped pipes."""
        header = _render_row(self.headings)
        separator = (
            "|"
            + "|".join("-" * (len(heading) + 2) for heading in self.headings)
            + "|"
        )
        rows = "\n".join(_render_row(row) for row in self.rows)
        return f"{header}\n{separator}" + (f"\n{rows}" if rows else "")

    def replace_in(
        self,
        document: str,
        replacement: MarkdownTable,
        *,
        preserve: Callable[[Mapping[str, str]], bool] | None = None,
        exclude: Callable[[Mapping[str, str]], bool] | None = None,
    ) -> str:
        """Replace this table, optionally preserving or excluding selected rows."""
        if self._start is None or self._end is None:
            raise MarkdownTableError("only an extracted table can replace document text")
        if self.headings != replacement.headings:
            raise MarkdownTableError("replacement headings do not match the extracted table")

        retained = tuple(
            row
            for row, record in zip(self.rows, self.records, strict=True)
            if preserve is not None and preserve(record)
        )
        rows = retained + replacement.rows
        if exclude is not None:
            rows = tuple(
                row
                for row in rows
                if not exclude(dict(zip(self.headings, row, strict=True)))
            )
        original = document[self._start : self._end]
        newline = "\r\n" if "\r\n" in original else "\n"
        rendered = MarkdownTable(
            self.headings,
            rows,
        ).render().replace("\n", newline)
        if original.endswith(newline):
            rendered += newline
        return document[: self._start] + rendered + document[self._end :]


def _render_row(values: Iterable[str]) -> str:
    cells = (str(value).replace("|", "\\|").replace("\n", " ") for value in values)
    return "| " + " | ".join(cells) + " |"


__all__ = ["MarkdownTable", "Column", "MarkdownTableError"]
