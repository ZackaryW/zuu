"""Cache-aware version checks against public GitHub raw configuration files."""

from __future__ import annotations

import json
import math
import re
import tomllib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol
from urllib.parse import quote

from zuu.case13 import deep_get
from zuu.case14 import loads as yaml_loads

__purpose__ = "Check cached GitHub configuration values for selected version changes."
__depends__ = ("case13", "case14")

_CACHE_SCHEMA = 1
_VERSION = re.compile(
    r"([0-9]+)\.([0-9]+)\.([0-9]+)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


class DocumentFormat(StrEnum):
    """Supported remote document formats, including suffix inference."""

    AUTO = "auto"
    YAML = "yaml"
    TOML = "toml"
    JSON = "json"


class ListenPolicy(StrEnum):
    """Built-in conditions that make a version check report true."""

    DIFFERENCE = "difference"
    MAJOR_CHANGE = "major_change"
    MINOR_CHANGE = "minor_change"
    MICRO_CHANGE = "micro_change"
    REGRESSION = "regression"


class CheckOrigin(StrEnum):
    """Where the document used for a successful check came from."""

    REMOTE = "remote"
    FRESH_CACHE = "fresh_cache"
    STALE_CACHE = "stale_cache"


class VersionCheckError(RuntimeError):
    """A remote version-check lifecycle could not complete."""


class SourceError(ValueError):
    """A GitHub source or check policy is invalid."""


class RemoteDocumentError(VersionCheckError):
    """A remote document could not be fetched, parsed, or traversed."""


class ComparisonError(VersionCheckError):
    """A listening policy or custom comparison could not produce a decision."""


@dataclass(frozen=True, slots=True)
class GitHubVersionSource:
    """Identify one value in a public GitHub raw configuration file."""

    owner: str
    repository: str
    path: str
    value_path: Iterable[str | int] = ("version",)
    ref: str = "HEAD"
    format: DocumentFormat | str = DocumentFormat.AUTO

    def __post_init__(self) -> None:
        owner = _repository_component(self.owner, "owner")
        repository = _repository_component(self.repository, "repository")
        ref = _single_line(self.ref, "ref")
        path = _repository_path(self.path)
        value_path = _value_path(self.value_path)
        try:
            selected_format = DocumentFormat(self.format)
        except (TypeError, ValueError) as error:
            raise SourceError(
                f"unsupported document format: {self.format!r}"
            ) from error
        if selected_format is DocumentFormat.AUTO:
            suffix = path.rsplit(".", 1)[-1].lower() if "." in path else ""
            inferred = {
                "yaml": DocumentFormat.YAML,
                "yml": DocumentFormat.YAML,
                "toml": DocumentFormat.TOML,
                "json": DocumentFormat.JSON,
            }.get(suffix)
            if inferred is None:
                raise SourceError(
                    "document format cannot be inferred from the file suffix"
                )
            selected_format = inferred
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "repository", repository)
        object.__setattr__(self, "ref", ref)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "value_path", value_path)
        object.__setattr__(self, "format", selected_format)

    @property
    def url(self) -> str:
        """Return the encoded HTTPS raw-content URL."""
        segments = [self.owner, self.repository, self.ref, *self.path.split("/")]
        encoded = "/".join(quote(segment, safe="") for segment in segments)
        return f"https://raw.githubusercontent.com/{encoded}"


@dataclass(frozen=True, slots=True)
class CheckPolicy:
    """Control cache freshness, failure fallback, and version listening."""

    max_age: timedelta = timedelta(hours=6)
    stale_if_error: bool = True
    listen: ListenPolicy | str = ListenPolicy.DIFFERENCE

    def __post_init__(self) -> None:
        if not isinstance(self.max_age, timedelta):
            raise SourceError("max_age must be a timedelta")
        seconds = self.max_age.total_seconds()
        if not math.isfinite(seconds) or seconds < 0:
            raise SourceError("max_age must be a finite nonnegative duration")
        if type(self.stale_if_error) is not bool:
            raise SourceError("stale_if_error must be a boolean")
        try:
            listen = ListenPolicy(self.listen)
        except (TypeError, ValueError) as error:
            raise SourceError(
                f"unsupported listening policy: {self.listen!r}"
            ) from error
        object.__setattr__(self, "listen", listen)


_DEFAULT_POLICY = CheckPolicy()


@dataclass(frozen=True, slots=True)
class VersionCheckResult:
    """Describe a comparison and the age and origin of its remote value."""

    supplied: Any
    remote: Any
    update_needed: bool
    origin: CheckOrigin
    checked_at: datetime
    refresh_error: RemoteDocumentError | None = field(default=None, compare=False)


class VersionCache(Protocol):
    """Replaceable byte storage for one remote-version cache record."""

    def read(self) -> bytes | None:
        """Return serialized cache bytes, or None when no record exists."""
        ...

    def write(self, data: bytes) -> None:
        """Replace the complete serialized cache record."""
        ...


class RawDocumentClient(Protocol):
    """Fetch text for a normalized public GitHub source."""

    def fetch(self, source: GitHubVersionSource) -> str:
        """Return the source document decoded as text."""
        ...


@dataclass(frozen=True, slots=True)
class _CacheRecord:
    checked_at: datetime
    text: str


def check_version(
    supplied: Any,
    source: GitHubVersionSource,
    *,
    cache: VersionCache | None = None,
    policy: CheckPolicy = _DEFAULT_POLICY,
    compare: Callable[[Any, Any], bool] | None = None,
    client: RawDocumentClient | None = None,
) -> VersionCheckResult:
    """Compare a supplied value with a cached or freshly fetched GitHub value.

    A custom comparison overrides the built-in listener. Remote acquisition
    failures can fall back to a matching stale cache; cache and comparison
    failures propagate and never publish a new record.
    """
    if not isinstance(source, GitHubVersionSource):
        raise TypeError("source must be a GitHubVersionSource")
    if not isinstance(policy, CheckPolicy):
        raise TypeError("policy must be a CheckPolicy")
    if compare is not None and not callable(compare):
        raise TypeError("compare must be callable or None")

    now = _utcnow()
    record = _read_cache(cache, source, now) if cache is not None else None
    if record is not None and now - record.checked_at < policy.max_age:
        try:
            remote = _extract(record.text, source)
        except RemoteDocumentError:
            record = None
        else:
            decision = _compare(supplied, remote, policy.listen, compare)
            return VersionCheckResult(
                supplied,
                remote,
                decision,
                CheckOrigin.FRESH_CACHE,
                record.checked_at,
            )

    try:
        text = _fetch(source, client)
        remote = _extract(text, source)
    except RemoteDocumentError as refresh_error:
        if record is None or not policy.stale_if_error:
            raise
        try:
            remote = _extract(record.text, source)
        except RemoteDocumentError:
            raise refresh_error
        decision = _compare(supplied, remote, policy.listen, compare)
        return VersionCheckResult(
            supplied,
            remote,
            decision,
            CheckOrigin.STALE_CACHE,
            record.checked_at,
            refresh_error,
        )

    decision = _compare(supplied, remote, policy.listen, compare)
    checked_at = _utcnow()
    if cache is not None:
        cache.write(_cache_bytes(source, policy, checked_at, text))
    return VersionCheckResult(
        supplied,
        remote,
        decision,
        CheckOrigin.REMOTE,
        checked_at,
    )


def _repository_component(value: str, label: str) -> str:
    value = _single_line(value, label)
    if value in (".", "..") or "/" in value or "\\" in value:
        raise SourceError(f"{label} must be one GitHub repository component")
    return value


def _single_line(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise SourceError(
            f"{label} must be a non-empty string without outer whitespace"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise SourceError(f"{label} must be a printable single-line string")
    return value


def _repository_path(value: str) -> str:
    value = _single_line(value, "path")
    if value.startswith("/") or "\\" in value:
        raise SourceError("path must be a forward-slash repository-relative path")
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise SourceError("path contains an empty, current, or parent segment")
    return value


def _value_path(keys: Iterable[str | int]) -> tuple[str | int, ...]:
    if isinstance(keys, (str, bytes, bytearray)):
        raise SourceError(
            "value_path must be an iterable of string keys and integer indexes"
        )
    try:
        path = tuple(keys)
    except TypeError as error:
        raise SourceError("value_path must be iterable") from error
    if any(type(key) not in (str, int) for key in path):
        raise SourceError("value_path keys must be strings or integers")
    return path


def _fetch(source: GitHubVersionSource, client: RawDocumentClient | None) -> str:
    if client is None:
        from .client import GitHubRawClient

        client = GitHubRawClient()
    try:
        text = client.fetch(source)
    except RemoteDocumentError:
        raise
    except Exception as error:
        raise RemoteDocumentError(
            f"could not fetch GitHub raw file: {source.url}"
        ) from error
    if not isinstance(text, str):
        raise RemoteDocumentError("raw document client must return text")
    return text


def _extract(text: str, source: GitHubVersionSource) -> Any:
    try:
        if source.format is DocumentFormat.YAML:
            document = yaml_loads(text)
        elif source.format is DocumentFormat.TOML:
            document = tomllib.loads(text)
        else:
            document = json.loads(text)
    except Exception as error:
        raise RemoteDocumentError(
            f"could not parse remote {source.format.value} document"
        ) from error
    try:
        return deep_get(document, source.value_path)
    except Exception as error:
        raise RemoteDocumentError(
            f"remote value path does not resolve: {source.value_path!r}"
        ) from error


def _compare(
    supplied: Any,
    remote: Any,
    listen: ListenPolicy,
    compare: Callable[[Any, Any], bool] | None,
) -> bool:
    if compare is not None:
        try:
            result = compare(supplied, remote)
        except Exception as error:
            raise ComparisonError("custom comparison failed") from error
        if type(result) is not bool:
            raise ComparisonError("custom comparison must return a boolean")
        return result
    if listen is ListenPolicy.DIFFERENCE:
        try:
            return bool(supplied != remote)
        except Exception as error:
            raise ComparisonError("difference comparison failed") from error

    local = _version_core(supplied, "supplied")
    candidate = _version_core(remote, "remote")
    if listen is ListenPolicy.MAJOR_CHANGE:
        return candidate[0] > local[0]
    if listen is ListenPolicy.MINOR_CHANGE:
        return candidate[0] == local[0] and candidate[1] > local[1]
    if listen is ListenPolicy.MICRO_CHANGE:
        return candidate[:2] == local[:2] and candidate[2] > local[2]
    return candidate < local


def _version_core(value: Any, label: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or (match := _VERSION.fullmatch(value)) is None:
        raise ComparisonError(
            f"{label} version must use major.minor.micro numeric syntax"
        )
    try:
        return tuple(int(part) for part in match.groups()[:3])  # type: ignore[return-value]
    except ValueError as error:
        raise ComparisonError(f"{label} version components are too large") from error


def _source_data(source: GitHubVersionSource) -> dict[str, object]:
    return {
        "format": source.format.value,
        "owner": source.owner,
        "path": source.path,
        "ref": source.ref,
        "repository": source.repository,
        "value_path": list(source.value_path),
    }


def _policy_data(policy: CheckPolicy) -> dict[str, object]:
    return {
        "listen": policy.listen.value,
        "max_age_seconds": policy.max_age.total_seconds(),
        "stale_if_error": policy.stale_if_error,
    }


def _cache_bytes(
    source: GitHubVersionSource,
    policy: CheckPolicy,
    checked_at: datetime,
    text: str,
) -> bytes:
    payload = {
        "checked_at": checked_at.isoformat(),
        "policy": _policy_data(policy),
        "schema": _CACHE_SCHEMA,
        "source": _source_data(source),
        "text": text,
    }
    return (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _read_cache(
    cache: VersionCache,
    source: GitHubVersionSource,
    now: datetime,
) -> _CacheRecord | None:
    data = cache.read()
    if data is None:
        return None
    if not isinstance(data, bytes):
        return None
    try:
        payload = json.loads(data)
        if not isinstance(payload, dict) or set(payload) != {
            "checked_at",
            "policy",
            "schema",
            "source",
            "text",
        }:
            return None
        if type(payload["schema"]) is not int or payload["schema"] != _CACHE_SCHEMA:
            return None
        if payload["source"] != _source_data(source):
            return None
        if not _valid_policy_data(payload["policy"]):
            return None
        if not isinstance(payload["text"], str) or not isinstance(
            payload["checked_at"], str
        ):
            return None
        checked_at = datetime.fromisoformat(payload["checked_at"])
        if checked_at.tzinfo is None or checked_at.utcoffset() != timedelta(0):
            return None
        checked_at = checked_at.astimezone(UTC)
        if checked_at > now:
            return None
    except (UnicodeError, ValueError, TypeError, RecursionError, OverflowError):
        return None
    return _CacheRecord(checked_at, payload["text"])


def _valid_policy_data(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "listen",
        "max_age_seconds",
        "stale_if_error",
    }:
        return False
    seconds = value["max_age_seconds"]
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
        return False
    if type(value["stale_if_error"]) is not bool:
        return False
    try:
        ListenPolicy(value["listen"])
    except (TypeError, ValueError):
        return False
    return True


def _utcnow() -> datetime:
    return datetime.now(UTC)


from .cache import FileVersionCache
from .client import GitHubRawClient

__all__ = [  # noqa: RUF022 - grouped by primary API, models, protocols, and errors
    "check_version",
    "GitHubVersionSource",
    "CheckPolicy",
    "VersionCheckResult",
    "DocumentFormat",
    "ListenPolicy",
    "CheckOrigin",
    "VersionCache",
    "RawDocumentClient",
    "FileVersionCache",
    "GitHubRawClient",
    "VersionCheckError",
    "SourceError",
    "RemoteDocumentError",
    "ComparisonError",
]
