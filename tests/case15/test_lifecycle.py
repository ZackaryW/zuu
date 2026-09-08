import json
from datetime import UTC, datetime, timedelta

import pytest

from zuu import case15
from zuu.case15 import (
    CheckOrigin,
    CheckPolicy,
    ComparisonError,
    GitHubVersionSource,
    ListenPolicy,
    RemoteDocumentError,
    check_version,
)


class MemoryCache:
    def __init__(self):
        self.data = None
        self.writes = []

    def read(self):
        return self.data

    def write(self, data):
        self.data = data
        self.writes.append(data)


class Client:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def fetch(self, source):
        self.calls += 1
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class ByteResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.payload


SOURCE = GitHubVersionSource("owner", "repo", "release.json")
T0 = datetime(2026, 4, 5, 6, 7, 8, tzinfo=UTC)


def set_time(monkeypatch, instant):
    monkeypatch.setattr(case15, "_utcnow", lambda: instant)


def populate(monkeypatch, cache, remote="2.0.0", policy=None):
    if policy is None:
        policy = CheckPolicy()
    set_time(monkeypatch, T0)
    client = Client(f'{{"version":"{remote}"}}')
    result = check_version("1.0.0", SOURCE, cache=cache, policy=policy, client=client)
    assert result.checked_at == T0
    return bytes(cache.data)


def test_default_six_hour_fresh_cache_avoids_network(monkeypatch) -> None:
    cache = MemoryCache()
    original = populate(monkeypatch, cache)
    set_time(monkeypatch, T0 + timedelta(hours=5, minutes=59, seconds=59))
    client = Client(RuntimeError("must not fetch"))

    result = check_version("2.0.0", SOURCE, cache=cache, client=client)

    assert result.origin is CheckOrigin.FRESH_CACHE
    assert result.checked_at == T0
    assert result.remote == "2.0.0"
    assert not result.update_needed
    assert result.refresh_error is None
    assert client.calls == 0
    assert cache.data == original


@pytest.mark.parametrize("max_age", [timedelta(hours=6), timedelta(0)])
def test_boundary_and_zero_age_require_refresh(monkeypatch, max_age) -> None:
    cache = MemoryCache()
    populate(monkeypatch, cache)
    set_time(monkeypatch, T0 + timedelta(hours=6))
    client = Client('{"version":"3.0.0"}')

    result = check_version(
        "1.0.0",
        SOURCE,
        cache=cache,
        policy=CheckPolicy(max_age=max_age),
        client=client,
    )

    assert result.origin is CheckOrigin.REMOTE
    assert result.checked_at == T0 + timedelta(hours=6)
    assert result.remote == "3.0.0"
    assert client.calls == 1
    assert len(cache.writes) == 2


@pytest.mark.parametrize(
    ("listen", "local", "remote", "expected"),
    [
        (ListenPolicy.DIFFERENCE, {"value": 1}, {"value": 1}, False),
        (ListenPolicy.DIFFERENCE, {"value": 1}, {"value": 2}, True),
        (ListenPolicy.MAJOR_CHANGE, "1.9.9", "2.0.0", True),
        (ListenPolicy.MAJOR_CHANGE, "1.2.3", "1.9.9", False),
        (ListenPolicy.MAJOR_CHANGE, "2.0.0", "1.9.9", False),
        (ListenPolicy.MINOR_CHANGE, "1.2.9", "1.3.0", True),
        (ListenPolicy.MINOR_CHANGE, "1.2.3", "2.0.0", False),
        (ListenPolicy.MINOR_CHANGE, "1.3.0", "1.2.9", False),
        (ListenPolicy.MICRO_CHANGE, "1.2.3", "1.2.4", True),
        (ListenPolicy.MICRO_CHANGE, "1.9.9", "2.0.0", False),
        (ListenPolicy.MICRO_CHANGE, "1.3.0", "1.2.9", False),
        (ListenPolicy.REGRESSION, "2.0.0", "1.9.9", True),
        (ListenPolicy.REGRESSION, "1.3.0", "1.2.9", True),
        (ListenPolicy.REGRESSION, "1.2.4", "1.2.3", True),
        (ListenPolicy.REGRESSION, "1.2.3", "1.3.0", False),
        (ListenPolicy.REGRESSION, "1.2.3", "1.2.3", False),
        (ListenPolicy.MICRO_CHANGE, "01.002.0003", "1.2.4", True),
        (ListenPolicy.MINOR_CHANGE, "1.2.3+4", "1.3.0+5", True),
        (ListenPolicy.REGRESSION, "1.2.3-beta", "1.2.3+4", False),
        (ListenPolicy.MAJOR_CHANGE, "1.2.3-beta", "1.2.3+4", False),
    ],
)
def test_listening_policies(monkeypatch, listen, local, remote, expected) -> None:
    set_time(monkeypatch, T0)
    source = GitHubVersionSource("owner", "repo", "release.json", [])
    result = check_version(
        local,
        source,
        policy=CheckPolicy(listen=listen),
        client=Client(json.dumps(remote)),
    )
    assert result.update_needed is expected


@pytest.mark.parametrize("value", ["1.2", "1.2.x", "v1.2.3", 123, None])
@pytest.mark.parametrize(
    "listen",
    [
        ListenPolicy.MAJOR_CHANGE,
        ListenPolicy.MINOR_CHANGE,
        ListenPolicy.MICRO_CHANGE,
        ListenPolicy.REGRESSION,
    ],
)
def test_numeric_listeners_reject_unsupported_values_and_preserve_cache(
    monkeypatch, value, listen
) -> None:
    cache = MemoryCache()
    populate(monkeypatch, cache)
    previous = bytes(cache.data)
    set_time(monkeypatch, T0 + timedelta(days=1))
    source = GitHubVersionSource("owner", "repo", "release.json", [])

    with pytest.raises(ComparisonError, match="version"):
        check_version(
            value,
            source,
            cache=cache,
            policy=CheckPolicy(max_age=timedelta(0), listen=listen),
            client=Client('"2.0.0"'),
        )
    assert cache.data == previous


def test_custom_comparison_overrides_listener_and_receives_raw_values(
    monkeypatch,
) -> None:
    set_time(monkeypatch, T0)
    source = GitHubVersionSource("owner", "repo", "release.json", [])
    calls = []

    def compare(local, remote):
        calls.append((local, remote))
        return remote["rank"] > local["rank"]

    result = check_version(
        {"rank": 2},
        source,
        policy=CheckPolicy(listen=ListenPolicy.MAJOR_CHANGE),
        compare=compare,
        client=Client('{"rank":3}'),
    )
    assert result.update_needed
    assert calls == [({"rank": 2}, {"rank": 3})]


@pytest.mark.parametrize("outcome", [1, None, "yes"])
def test_custom_comparison_requires_exact_bool_and_preserves_cache(
    monkeypatch, outcome
) -> None:
    cache = MemoryCache()
    previous = populate(monkeypatch, cache)
    set_time(monkeypatch, T0 + timedelta(days=1))

    with pytest.raises(ComparisonError, match="boolean"):
        check_version(
            "1.0.0",
            SOURCE,
            cache=cache,
            policy=CheckPolicy(max_age=timedelta(0)),
            compare=lambda local, remote: outcome,
            client=Client('{"version":"3.0.0"}'),
        )
    assert cache.data == previous


def test_custom_comparison_exception_is_preserved_and_cache_unchanged(
    monkeypatch,
) -> None:
    cache = MemoryCache()
    previous = populate(monkeypatch, cache)
    set_time(monkeypatch, T0 + timedelta(days=1))
    failure = LookupError("comparison failed")

    def compare(local, remote):
        raise failure

    with pytest.raises(ComparisonError, match="custom comparison") as error:
        check_version(
            "1.0.0",
            SOURCE,
            cache=cache,
            policy=CheckPolicy(max_age=timedelta(0)),
            compare=compare,
            client=Client('{"version":"3.0.0"}'),
        )
    assert error.value.__cause__ is failure
    assert cache.data == previous


@pytest.mark.parametrize(
    "response",
    [RuntimeError("offline"), "not json", "{}"],
)
def test_refresh_acquisition_failure_uses_matching_stale_cache(
    monkeypatch, response
) -> None:
    cache = MemoryCache()
    previous = populate(monkeypatch, cache)
    set_time(monkeypatch, T0 + timedelta(days=1))

    result = check_version("1.0.0", SOURCE, cache=cache, client=Client(response))

    assert result.origin is CheckOrigin.STALE_CACHE
    assert result.remote == "2.0.0"
    assert result.checked_at == T0
    assert result.update_needed
    assert isinstance(result.refresh_error, RemoteDocumentError)
    assert cache.data == previous


def test_refresh_decode_failure_uses_stale_cache(monkeypatch) -> None:
    cache = MemoryCache()
    populate(monkeypatch, cache)
    set_time(monkeypatch, T0 + timedelta(days=1))
    monkeypatch.setattr(
        "zuu.case15.client.urlopen", lambda *args, **kwargs: ByteResponse(b"\xff")
    )

    result = check_version("1.0.0", SOURCE, cache=cache)

    assert result.origin is CheckOrigin.STALE_CACHE
    assert isinstance(result.refresh_error.__cause__, UnicodeDecodeError)


def test_stale_fallback_can_be_disabled_without_comparing(monkeypatch) -> None:
    cache = MemoryCache()
    previous = populate(monkeypatch, cache)
    set_time(monkeypatch, T0 + timedelta(days=1))
    comparisons = []

    with pytest.raises(RemoteDocumentError):
        check_version(
            "1.0.0",
            SOURCE,
            cache=cache,
            policy=CheckPolicy(stale_if_error=False),
            compare=lambda *values: comparisons.append(values) or True,
            client=Client(RuntimeError("offline")),
        )
    assert comparisons == []
    assert cache.data == previous


@pytest.mark.parametrize("cache_state", ["missing", "corrupt", "mismatched"])
def test_missing_corrupt_or_mismatched_cache_cannot_fallback(
    monkeypatch, cache_state
) -> None:
    cache = MemoryCache()
    if cache_state != "missing":
        populate(monkeypatch, cache)
    if cache_state == "corrupt":
        cache.data = b"not-json"
    elif cache_state == "mismatched":
        payload = json.loads(cache.data)
        payload["source"]["repository"] = "another-repository"
        cache.data = json.dumps(payload).encode()
    set_time(monkeypatch, T0 + timedelta(days=1))
    previous = cache.data

    with pytest.raises(RemoteDocumentError) as error:
        check_version(
            "1.0.0", SOURCE, cache=cache, client=Client(RuntimeError("offline"))
        )
    assert isinstance(error.value.__cause__, RuntimeError)
    assert cache.data == previous


def test_unparseable_stale_cache_preserves_primary_refresh_error(monkeypatch) -> None:
    cache = MemoryCache()
    populate(monkeypatch, cache)
    payload = json.loads(cache.data)
    payload["text"] = "not json"
    cache.data = json.dumps(payload).encode()
    set_time(monkeypatch, T0 + timedelta(days=1))
    failure = RuntimeError("offline")

    with pytest.raises(RemoteDocumentError) as error:
        check_version("1.0.0", SOURCE, cache=cache, client=Client(failure))
    assert error.value.__cause__ is failure


def test_invalid_fresh_cached_text_is_refreshed(monkeypatch) -> None:
    cache = MemoryCache()
    populate(monkeypatch, cache)
    payload = json.loads(cache.data)
    payload["text"] = "not json"
    cache.data = json.dumps(payload).encode()
    set_time(monkeypatch, T0 + timedelta(minutes=1))
    client = Client('{"version":"3.0.0"}')

    result = check_version("1.0.0", SOURCE, cache=cache, client=client)
    assert result.origin is CheckOrigin.REMOTE
    assert result.remote == "3.0.0"
    assert client.calls == 1


def test_stale_comparison_error_does_not_fall_back_again(monkeypatch) -> None:
    cache = MemoryCache()
    populate(monkeypatch, cache, remote="invalid")
    set_time(monkeypatch, T0 + timedelta(days=1))

    with pytest.raises(ComparisonError):
        check_version(
            "1.0.0",
            SOURCE,
            cache=cache,
            policy=CheckPolicy(listen=ListenPolicy.MAJOR_CHANGE),
            client=Client(RuntimeError("offline")),
        )


def test_no_cache_always_fetches(monkeypatch) -> None:
    set_time(monkeypatch, T0)
    client = Client('{"version":"2.0.0"}')
    first = check_version("1.0.0", SOURCE, client=client)
    second = check_version("1.0.0", SOURCE, client=client)
    assert first.origin is second.origin is CheckOrigin.REMOTE
    assert client.calls == 2
