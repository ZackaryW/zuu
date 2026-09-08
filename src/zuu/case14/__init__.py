"""A small reader for an explicitly limited YAML subset."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Any

__purpose__ = (
    "Read simple YAML configuration with nested mappings, lists, and scalar values."
)
__depends__ = ()


@dataclass(frozen=True, slots=True)
class UnsupportedYaml:
    """An opaque YAML value, retained as raw text instead of interpreted."""

    raw: str


class YamlError(ValueError):
    """Malformed or unsupported YAML, with a one-based source line number."""

    def __init__(self, message: str, line: int) -> None:
        self.line = line
        super().__init__(f"line {line}: {message}")


def loads(text: str) -> Any:
    """Read one simple YAML document from text; empty input returns None.

    Supports block mappings with string keys, block lists, single-line scalars,
    comments, and empty []/{} containers. Unsupported values are preserved as
    UnsupportedYaml; malformed structure raises YamlError.
    """
    if not isinstance(text, str):
        raise TypeError("loads requires a string")
    lines = _lines(text)
    if not lines:
        return None
    if lines[0].indent:
        raise YamlError("the root must start at column one", lines[0].number)
    parser = _Parser(lines)
    result = parser.block(0)
    if parser.position != len(lines):
        raise YamlError(
            "unexpected indentation or mixed block types", parser.peek().number
        )
    return result


def load(path: str | PathLike[str], *, encoding: str = "utf-8") -> Any:
    """Read a file without modifying it; filesystem and decoding errors propagate."""
    return loads(Path(path).read_text(encoding=encoding))


@dataclass(frozen=True, slots=True)
class _Line:
    indent: int
    text: str
    number: int
    opaque: UnsupportedYaml | None = None
    colon: int | None = None


def _scan(text: str, number: int, *, split: bool = False) -> tuple[str, int | None]:
    """Locate a mapping colon and strip comments outside quoted tokens."""
    quote = None
    colon = None
    token_start = True
    index = 0
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\" and quote == '"':
                index += 2
                continue
            if char == quote:
                if quote == "'" and text[index : index + 2] == "''":
                    index += 2
                    continue
                quote = None
        elif char == "#" and (index == 0 or text[index - 1] in " \t"):
            return text[:index].rstrip(), colon
        elif char in "\"'" and token_start:
            quote = char
            token_start = False
        elif char == ":" and (index + 1 == len(text) or text[index + 1] in " \t"):
            if split:
                return text, index
            if colon is None:
                colon = index
            token_start = True
        elif char not in " \t":
            token_start = False
        index += 1
    if quote and not split:
        raise YamlError("unterminated quote; multiline strings are unsupported", number)
    return text.rstrip(), colon


def _lines(text: str) -> list[_Line]:
    result = []
    text = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    source = text.split("\n")
    index = 0
    while index < len(source):
        number = index + 1
        raw = source[index]
        index += 1
        if re.search(
            r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff\ufffe\uffff]", raw
        ):
            raise YamlError("unsupported control or Unicode character", number)
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw[indent:]
        if content.startswith("\t"):
            raise YamlError("indentation must use spaces", number)
        parent_indent = indent
        # Expand compact sequence entries into a dash and an indented node.
        while content == "-" or content.startswith(("- ", "-\t")):
            parent_indent = indent
            result.append(_Line(indent, "-", number))
            remainder = content[1:].lstrip(" ")
            if remainder.startswith("\t"):
                raise YamlError("sequence indentation must use spaces", number)
            indent += len(content) - len(remainder)
            content = remainder
        opaque = None
        # Split only the key: an opaque value may contain arbitrary YAML syntax.
        if content.startswith(("[", "{", "&", "*", "!", "|", ">")):
            colon = None
        else:
            content, colon = _scan(content, number, split=True)
        value = content[colon + 1 :].lstrip() if colon is not None else content
        multiline_quote = False
        if value.startswith(("'", '"')):
            try:
                _scan(value, number)
            except YamlError:
                multiline_quote = True
        if multiline_quote or value.startswith(("[", "{", "&", "*", "!", "|", ">")):
            simple = value.split("#", 1)[0].rstrip()
            if simple not in ("[]", "{}"):
                pieces = [value]
                if multiline_quote or value.startswith(("[", "{")):
                    index = _flow_end(source, index, pieces, number)
                else:
                    # A block scalar, anchor, or tag owns its indented body.
                    while index < len(source):
                        following = source[index]
                        owner_indent = indent if colon is not None else parent_indent
                        if (
                            following.strip()
                            and len(following) - len(following.lstrip(" "))
                            <= owner_indent
                        ):
                            break
                        pieces.append(following)
                        index += 1
                opaque = UnsupportedYaml("\n".join(pieces))
        if opaque is None:
            content, _ = _scan(content, number)
        if content:
            if content in ("---", "...") or content.startswith(("--- ", "... ", "%")):
                raise YamlError(
                    "document markers and directives are unsupported", number
                )
            result.append(_Line(indent, content, number, opaque, colon))
    return result


def _flow_end(source: list[str], index: int, pieces: list[str], number: int) -> int:
    """Find a flow or quoted value's end without interpreting its contents."""
    stack = []
    quote = None
    escaped = False
    token_start = True
    while True:
        for offset, char in enumerate(pieces[-1]):
            closed = False
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\" and quote == '"':
                    escaped = True
                elif char == quote:
                    if quote == "'" and pieces[-1][offset : offset + 2] == "''":
                        escaped = True
                    else:
                        quote = None
                        closed = not stack
                if not closed:
                    continue
            elif char == "#" and (offset == 0 or pieces[-1][offset - 1] in " \t"):
                break
            elif char in "\"'" and token_start:
                quote = char
            elif char in "[{":
                stack.append(char)
            elif char in "]}":
                if not stack or stack.pop() != {"]": "[", "}": "{"}[char]:
                    raise YamlError("mismatched flow delimiters", number)
                closed = not stack
            if closed:
                tail = pieces[-1][offset + 1 :]
                if tail and not (
                    tail[0] in " \t" and not tail.lstrip().split("#", 1)[0]
                ):
                    raise YamlError("unexpected text after opaque value", number)
                return index
            if char not in " \t":
                token_start = char in "[{,:"
        if index == len(source):
            raise YamlError("unterminated flow or quoted value", number)
        pieces.append(source[index])
        index += 1


class _Parser:
    def __init__(self, lines: list[_Line]) -> None:
        self.lines = lines
        self.position = 0
        self.depth = 0

    def peek(self) -> _Line:
        return self.lines[self.position]

    def child(self, indent: int) -> Any:
        if self.position < len(self.lines) and self.peek().indent > indent:
            return self.block(self.peek().indent)
        return None

    def block(self, indent: int) -> Any:
        self.depth += 1
        if self.depth > 100:
            raise YamlError("nesting exceeds 100 levels", self.peek().number)
        first = self.peek()
        is_list = first.text == "-"
        colon = first.colon
        if not is_list and colon is None:
            self.position += 1
            result = (
                first.opaque
                if first.opaque is not None
                else _scalar(first.text, first.number)
            )
        else:
            result = [] if is_list else {}
            while self.position < len(self.lines) and self.peek().indent == indent:
                line = self.peek()
                text, colon = line.text, line.colon
                if is_list:
                    if text != "-":
                        break
                    self.position += 1
                    result.append(self.child(indent))
                else:
                    if colon is None or text == "-":
                        break
                    key = _scalar(text[:colon].strip(), line.number)
                    if not isinstance(key, str):
                        raise YamlError(
                            "mapping keys must be strings; quote this key", line.number
                        )
                    if key in result:
                        raise YamlError(f"duplicate key {key!r}", line.number)
                    self.position += 1
                    value = text[colon + 1 :].strip()
                    result[key] = (
                        line.opaque
                        if line.opaque is not None
                        else (
                            _scalar(value, line.number) if value else self.child(indent)
                        )
                    )
        self.depth -= 1
        return result


def _scalar(text: str, number: int) -> Any:
    text, _ = _scan(text, number)
    if not text:
        return None
    if text.startswith('"'):
        try:
            value = json.loads(text)
        except ValueError as error:
            if re.fullmatch(r'"(?:[^"\\]|\\.)*"', text):
                return UnsupportedYaml(text)
            raise YamlError(
                "invalid double-quoted string (use JSON escapes)", number
            ) from error
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise YamlError("unpaired Unicode surrogate", number)
        return value
    if text.startswith("'"):
        if not re.fullmatch(r"'(?:[^']|'')*'", text):
            raise YamlError("invalid single-quoted string", number)
        return text[1:-1].replace("''", "'")
    if text == "[]":
        return []
    if text == "{}":
        return {}
    if (
        text[0] in "[]{}&*!|>%@`"
        or text in ("?", ":", "-")
        or text.startswith(("? ", ": ", "- "))
    ):
        raise YamlError("unsupported YAML syntax; quote literal strings", number)
    if _scan(text, number)[1] is not None:
        raise YamlError("a plain scalar cannot contain ': '; quote it", number)
    if text in ("null", "Null", "NULL", "~"):
        return None
    if text in ("true", "True", "TRUE", "false", "False", "FALSE"):
        return text.lower() == "true"
    if re.fullmatch(r"[-+]?[0-9]+", text):
        try:
            return int(text)
        except ValueError as error:
            raise YamlError(
                "integer exceeds Python's conversion limit", number
            ) from error
    if re.fullmatch(r"[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?", text):
        return float(text)
    if re.fullmatch(r"0[oOxXbB][0-9a-fA-F]+|[-+]?\.(?:inf|nan)", text, re.IGNORECASE):
        return UnsupportedYaml(text)
    return text


# The first export is the primary utility shown in the generated case index.
__all__ = ["loads", "load", "UnsupportedYaml", "YamlError"]  # noqa: RUF022
