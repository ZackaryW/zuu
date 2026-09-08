import json
from datetime import UTC, datetime, timedelta

import pytest

from zuu import case15
from zuu.case15 import (
    CheckOrigin,
    CheckPolicy,
    FileVersionCache,
    GitHubVersionSource,
    ListenPolicy,
    check_version,
)


class MemoryCache:
    def __init__(self, data=None):
        self.data = data
        self.reads = 0
        self.writes = []

    def read(self):
        self.reads += 1
        return self.data

    def write(self, data):
        self.writes.append(data)
        self.data = data


class TextClient:
    def __init__(self, text):
        self.text = text
        self.calls = 0

    def fetch(self, source):
        self.calls += 1
        return self.text


def fixed_clock(monkeypatch, instant):
    monkeypatch.setattr(case15, "_utcnow", lambda: instant)


def seed_cache(monkeypatch, *, text='{"version":"2.0.0"}', policy=None):
    if policy is None:
        policy = CheckPolicy()
    instant = datetime(2026, 1, 2, 3, 4, 5, 6789, tzinfo=UTC)
    fixed_clock(monkeypatch, instant)
    source = GitHubVersionSource("owner", "repo", "release.json")
    cache = MemoryCache()
    check_version("1.0.0", source, cache=cache, policy=policy, client=TextClient(text))
    return source, cache, instant


def test_file_cache_missing_read_and_exact_round_trip(tmp_path) -> None:
    cache = FileVersionCache(tmp_path / "nested" / "version.cache")
    assert cache.read() is None

    cache.write(b"first\x00record")
    assert cache.read() == b"first\x00record"
    cache.write(b"replacement")
    assert cache.read() == b"replacement"
    assert cache == FileVersionCache(tmp_path / "nested" / "version.cache")
    assert "version.cache" in repr(cache)


def test_file_cache_requires_bytes(tmp_path) -> None:
    cache = FileVersionCache(tmp_path / "version.cache")
    with pytest.raises(TypeError, match="bytes"):
        cache.write("text")


def test_file_cache_replace_failure_preserves_target_and_cleans_temp(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "version.cache"
    path.write_bytes(b"old")
    cache = FileVersionCache(path)

    def fail_replace(source, target):
        raise OSError("replace denied")

    monkeypatch.setattr("zuu.case15.cache.os.replace", fail_replace)
    with pytest.raises(OSError, match="replace denied"):
        cache.write(b"new")

    assert path.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [path]


def test_cache_record_is_deterministic_and_complete(monkeypatch) -> None:
    policy = CheckPolicy(
        max_age=timedelta(minutes=90),
        stale_if_error=False,
        listen=ListenPolicy.MINOR_CHANGE,
    )
    source, first, instant = seed_cache(monkeypatch, policy=policy)
    second = MemoryCache()
    check_version(
        "1.0.0",
        source,
        cache=second,
        policy=policy,
        client=TextClient('{"version":"2.0.0"}'),
    )

    assert first.data == second.data
    assert first.data.endswith(b"\n")
    payload = json.loads(first.data)
    assert payload == {
        "checked_at": instant.isoformat(),
        "policy": {
            "listen": "minor_change",
            "max_age_seconds": 5400.0,
            "stale_if_error": False,
        },
        "schema": 1,
        "source": {
            "format": "json",
            "owner": "owner",
            "path": "release.json",
            "ref": "HEAD",
            "repository": "repo",
            "value_path": ["version"],
        },
        "text": '{"version":"2.0.0"}',
    }
    assert "callback" not in payload


def _alter_record(data, alteration):
    if alteration == "invalid-json":
        return b"not json"
    if alteration == "wrong-type":
        return b"[]"
    if alteration == "extra-field":
        payload = json.loads(data)
        payload["extra"] = True
    elif alteration == "schema":
        payload = json.loads(data)
        payload["schema"] = 2
    elif alteration == "source":
        payload = json.loads(data)
        payload["source"]["owner"] = "someone-else"
    elif alteration == "future":
        payload = json.loads(data)
        payload["checked_at"] = "2099-01-01T00:00:00+00:00"
    elif alteration == "naive-time":
        payload = json.loads(data)
        payload["checked_at"] = "2026-01-02T03:04:05"
    elif alteration == "non-utc-time":
        payload = json.loads(data)
        payload["checked_at"] = "2026-01-02T03:04:05+01:00"
    elif alteration == "invalid-policy":
        payload = json.loads(data)
        payload["policy"]["listen"] = "anything"
    elif alteration == "wrong-text-type":
        payload = json.loads(data)
        payload["text"] = ["not", "text"]
    else:
        raise AssertionError(alteration)
    return json.dumps(payload).encode()


@pytest.mark.parametrize(
    "alteration",
    [
        "invalid-json",
        "wrong-type",
        "extra-field",
        "schema",
        "source",
        "future",
        "naive-time",
        "non-utc-time",
        "invalid-policy",
        "wrong-text-type",
    ],
)
def test_unusable_cache_records_are_ignored(monkeypatch, alteration) -> None:
    source, cache, instant = seed_cache(monkeypatch)
    cache.data = _alter_record(cache.data, alteration)
    fixed_clock(monkeypatch, instant + timedelta(minutes=1))
    client = TextClient('{"version":"3.0.0"}')

    result = check_version("1.0.0", source, cache=cache, client=client)

    assert result.remote == "3.0.0"
    assert result.origin is CheckOrigin.REMOTE
    assert client.calls == 1
    assert len(cache.writes) == 2


def test_wrong_cache_byte_type_is_ignored(monkeypatch) -> None:
    source = GitHubVersionSource("owner", "repo", "release.json")
    cache = MemoryCache("not bytes")
    client = TextClient('{"version":"3.0.0"}')
    result = check_version("1.0.0", source, cache=cache, client=client)
    assert result.origin is CheckOrigin.REMOTE
    assert client.calls == 1


def test_current_policy_reuses_record_with_different_recorded_policy(
    monkeypatch,
) -> None:
    old_policy = CheckPolicy(
        max_age=timedelta(minutes=5), listen=ListenPolicy.DIFFERENCE
    )
    source, cache, instant = seed_cache(monkeypatch, policy=old_policy)
    fixed_clock(monkeypatch, instant + timedelta(hours=2))
    client = TextClient('{"version":"9.0.0"}')
    current = CheckPolicy(max_age=timedelta(hours=3), listen=ListenPolicy.MAJOR_CHANGE)

    result = check_version("1.0.0", source, cache=cache, policy=current, client=client)

    assert result.origin is CheckOrigin.FRESH_CACHE
    assert result.remote == "2.0.0"
    assert result.update_needed
    assert client.calls == 0
    assert len(cache.writes) == 1


def test_cache_read_failure_propagates_before_network() -> None:
    class FailingCache:
        def read(self):
            raise OSError("read denied")

        def write(self, data):
            raise AssertionError("not reached")

    client = TextClient('{"version":"2.0.0"}')
    source = GitHubVersionSource("owner", "repo", "release.json")
    with pytest.raises(OSError, match="read denied"):
        check_version("1.0.0", source, cache=FailingCache(), client=client)
    assert client.calls == 0


def test_cache_write_failure_propagates_after_comparison() -> None:
    class FailingCache:
        def read(self):
            return None

        def write(self, data):
            raise OSError("write denied")

    source = GitHubVersionSource("owner", "repo", "release.json")
    with pytest.raises(OSError, match="write denied"):
        check_version(
            "1.0.0",
            source,
            cache=FailingCache(),
            client=TextClient('{"version":"2.0.0"}'),
        )
