import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path

from zuu import case15
from zuu.case15 import (
    CheckOrigin,
    CheckPolicy,
    GitHubVersionSource,
    ListenPolicy,
    check_version,
)


class ApplicationCache:
    def __init__(self):
        self.payload = None

    def read(self):
        return self.payload

    def write(self, data):
        self.payload = data


class ApplicationClient:
    def __init__(self, documents):
        self.documents = documents
        self.requests = []

    def fetch(self, source):
        self.requests.append(source.url)
        return self.documents[source.path]


def test_yaml_cache_listener_change_and_custom_comparison(monkeypatch) -> None:
    source = GitHubVersionSource(
        "example",
        "versions",
        "pubspec.yaml",
        ["packages", "application", "version"],
        ref="main",
    )
    client = ApplicationClient(
        {
            "pubspec.yaml": (
                "packages:\n  application:\n    version: 2.4.1+8\n    channel: stable\n"
            )
        }
    )
    cache = ApplicationCache()
    instant = datetime(2026, 7, 8, 9, 10, tzinfo=UTC)
    monkeypatch.setattr(case15, "_utcnow", lambda: instant)

    remote = check_version("1.9.9", source, cache=cache, client=client)
    assert remote.origin is CheckOrigin.REMOTE
    assert remote.remote == "2.4.1+8"
    assert remote.update_needed

    monkeypatch.setattr(case15, "_utcnow", lambda: instant + timedelta(hours=1))
    major = check_version(
        "1.9.9",
        source,
        cache=cache,
        policy=CheckPolicy(listen=ListenPolicy.MAJOR_CHANGE),
        client=client,
    )
    assert major.origin is CheckOrigin.FRESH_CACHE
    assert major.update_needed

    calls = []
    custom = check_version(
        {"accepted": "2.4.1+8"},
        source,
        cache=cache,
        policy=CheckPolicy(listen=ListenPolicy.REGRESSION),
        compare=lambda local, candidate: (
            calls.append((local, candidate)) or local["accepted"] == candidate
        ),
        client=client,
    )
    assert custom.origin is CheckOrigin.FRESH_CACHE
    assert custom.update_needed
    assert calls == [({"accepted": "2.4.1+8"}, "2.4.1+8")]
    assert client.requests == [source.url]


def test_toml_and_json_use_same_protocol_boundaries() -> None:
    documents = {
        "release.toml": '[release]\nversions = ["1.0.0", "1.1.0"]\n',
        "release.json": '{"release":{"versions":["2.0.0","2.0.1"]}}',
    }
    client = ApplicationClient(documents)
    cases = [
        ("release.toml", "1.1.0"),
        ("release.json", "2.0.1"),
    ]
    for path, expected in cases:
        source = GitHubVersionSource(
            "example", "versions", path, ["release", "versions", 1]
        )
        result = check_version("0.0.0", source, client=client)
        assert result.remote == expected


def test_case15_declares_and_imports_only_its_direct_case_dependencies() -> None:
    assert case15.__depends__ == ("case13", "case14")
    imported_cases = set()
    source_root = Path(case15.__file__).parent
    for module_path in source_root.glob("*.py"):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_cases.update(
                    alias.name
                    for alias in node.names
                    if alias.name.startswith("zuu.case")
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("zuu.case")
            ):
                imported_cases.add(node.module)
    assert imported_cases == {"zuu.case13", "zuu.case14"}
