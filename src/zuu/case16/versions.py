"""Comparable numeric version keys, without a third-party packaging library."""

import re

VersionKey = tuple[tuple[int, ...], bool, tuple[tuple[int, int | str], ...]]
_VERSION = re.compile(
    r"[vV]?(?P<core>[0-9]+(?:\.[0-9]+)*)"
    r"(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\Z"
)


def parse_version(value: str) -> VersionKey | None:
    """Parse a full numeric dotted tag, optionally prefixed with v or V.

    Return a sortable key or None for an unsupported name. Numeric components
    compare numerically; trailing zero components and leading zeroes have no
    significance. Prereleases sort below the corresponding stable version and
    use SemVer-style numeric/text identifier ordering. Build metadata is ignored.
    This accepts variable-length numeric cores, including calendar versions.
    """
    if not isinstance(value, str):
        return None
    match = _VERSION.fullmatch(value)
    if match is None:
        return None
    core = [int(part) for part in match["core"].split(".")]
    while len(core) > 1 and core[-1] == 0:
        core.pop()
    prerelease = match["pre"]
    identifiers = tuple(
        (0, int(part)) if part.isascii() and part.isdigit() else (1, part)
        for part in prerelease.split(".")
    ) if prerelease else ()
    return tuple(core), prerelease is None, identifiers
