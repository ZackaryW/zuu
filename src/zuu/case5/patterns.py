"""Validation and translation for the repository glob dialect."""

import re
from functools import cache
from pathlib import PurePosixPath


WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


def normalize_relative(value: str, *, label: str = "repository path") -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    if (
        not value
        or "\x00" in value
        or "\\" in value
        or value.startswith("/")
        or WINDOWS_DRIVE.match(value)
    ):
        raise ValueError(f"invalid {label}: {value!r}")
    path = PurePosixPath(value)
    if (
        path.as_posix() != value
        or value == "."
        or any(part == ".." for part in path.parts)
    ):
        raise ValueError(f"invalid {label}: {value!r}")
    return path.as_posix()


def validate_pattern(pattern: str) -> None:
    normalize_relative(pattern)
    if any("**" in segment and segment != "**" for segment in pattern.split("/")):
        raise ValueError("repository glob requires ** to occupy a complete segment")
    opened: int | None = None
    for index, character in enumerate(pattern):
        if character == "[":
            if opened is not None:
                raise ValueError("repository glob has nested character classes")
            opened = index
        elif character == "]":
            if opened is None:
                raise ValueError("repository glob has an unmatched closing bracket")
            if pattern[opened + 1 : index] in {"", "!"}:
                raise ValueError("repository glob has an empty character class")
            opened = None
    if opened is not None:
        raise ValueError("repository glob has an unclosed character class")
    try:
        compile_pattern(pattern)
    except re.error as error:
        raise ValueError(f"invalid repository glob: {error}") from error


@cache
def compile_pattern(pattern: str) -> re.Pattern[str]:
    segments = pattern.split("/")
    translated: list[str] = []
    for index, segment in enumerate(segments):
        last = index == len(segments) - 1
        if segment == "**":
            translated.append(".*" if last else "(?:.*/)?")
        else:
            translated.append(_translate_segment(segment))
            if not last:
                translated.append("/")
    return re.compile("".join(translated) + r"\Z")


def _translate_segment(segment: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(segment):
        character = segment[index]
        if character == "*":
            result.append("[^/]*")
            index += 1
        elif character == "?":
            result.append("[^/]")
            index += 1
        elif character == "[":
            end = segment.index("]", index + 1)
            body = segment[index + 1 : end].replace("\\", "\\\\")
            if body.startswith("!"):
                body = "^" + body[1:]
            result.append("[" + body + "]")
            index = end + 1
        else:
            result.append(re.escape(character))
            index += 1
    return "".join(result)
