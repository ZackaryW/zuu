from __future__ import annotations

import json
import os
import stat
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

from zuu.case12 import GitHubSubpath, GitHubSubpathError


SHA = "a" * 40
MARKER = ".zuu-filters.json"
PREFIX = "wrapper/templates/python/"
FILES = {
    "app.py",
    "README.md",
    "nested/data.txt",
    "nested/UPPER.PY",
    "tests/test_app.py",
}


class ArchiveClient:
    def __init__(self, entries: list[tuple[str | ZipInfo, bytes]] | None = None):
        stream = BytesIO()
        with ZipFile(stream, "w") as archive:
            for name, content in (
                entries
                if entries is not None
                else [
                    *((PREFIX + name, name.encode()) for name in sorted(FILES)),
                    (PREFIX + "empty/", b""),
                    (PREFIX + "nested/", b""),
                    ("wrapper/elsewhere.txt", b"unrelated"),
                ]
            ):
                archive.writestr(name, content)
        self.archive = stream.getvalue()
        self.downloads = []
        self.resolutions = []

    def resolve_commit(self, owner, repository, branch):
        self.resolutions.append((owner, repository, branch))
        return SHA

    def download_archive(self, owner, repository, commit, destination):
        self.downloads.append((owner, repository, commit))
        destination.write_bytes(self.archive)


def source(**kwargs) -> GitHubSubpath:
    return GitHubSubpath("org", "repo", "templates/python", commit=SHA, **kwargs)


def files(target: Path) -> set[str]:
    return {
        p.relative_to(target).as_posix()
        for p in target.rglob("*")
        if p.is_file() and p.name not in {".commit", MARKER}
    }


@pytest.mark.parametrize(
    ("include", "exclude", "expected"),
    [
        ((), (), FILES),
        ((r"\.py$", r"\.md$"), (r"^tests/", r"^README"), {"app.py"}),
        ((r"\.md$", r"\.py$"), (r"^README", r"^tests/"), {"app.py"}),
        ((), (r"^tests/", r"\.txt$"), {"app.py", "README.md", "nested/UPPER.PY"}),
        ((r"^nested/.*\.txt$",), (), {"nested/data.txt"}),
        ((r"(?i)\.py$",), (), {"app.py", "nested/UPPER.PY", "tests/test_app.py"}),
        ((), (r"^tests$",), FILES),
        ((r"^templates/",), (), set()),
        (("",), (), FILES),
        ((), ("",), set()),
    ],
)
def test_filter_selection(tmp_path, include, exclude, expected):
    client = ArchiveClient()
    target = tmp_path / "target"
    result = source(include=include, exclude=exclude).sync(target, client=client)
    assert result.changed
    assert files(target) == expected
    assert client.downloads == [("org", "repo", SHA)]
    assert (target / "empty").exists() == (not include and not exclude)
    assert not list(tmp_path.glob(".target.zuu-*"))


@pytest.mark.parametrize("filters", [{"include": ("no-match",)}, {"exclude": (".*",)}])
def test_no_matches_replace_old_content_and_cache(tmp_path, filters):
    target = tmp_path / "target"
    client = ArchiveClient()
    source().sync(target, client=client)
    selected = source(**filters)
    assert selected.sync(target, client=client).changed
    assert {p.name for p in target.iterdir()} == {".commit", MARKER}
    assert not selected.sync(target).changed


@pytest.mark.parametrize(
    "entries",
    [
        [("wrapper/other/file", b"x")],
        [(PREFIX.rstrip("/"), b"file")],
        [(PREFIX, b"")],
        [("wrapper/../outside", b"x"), (PREFIX + "app.py", b"x")],
        [("other/a", b"x"), (PREFIX + "app.py", b"x")],
    ],
)
def test_filters_do_not_hide_source_or_archive_errors(tmp_path, entries):
    target = tmp_path / "target"
    target.mkdir()
    (target / "old").write_bytes(b"old")
    with pytest.raises(GitHubSubpathError):
        source(exclude=(".*",)).sync(target, client=ArchiveClient(entries))
    assert files(target) == {"old"}


@pytest.mark.parametrize(
    "name", [".commit", ".commit/child", MARKER, MARKER + "/child"]
)
def test_reserved_names_rejected_even_when_excluded(tmp_path, name):
    with pytest.raises(GitHubSubpathError, match="reserved"):
        source(exclude=(".*",)).sync(
            tmp_path / "target", client=ArchiveClient([(PREFIX + name, b"x")])
        )


@pytest.mark.parametrize("kind", [stat.S_IFLNK, stat.S_IFIFO])
def test_excluded_special_entries_are_rejected(tmp_path, kind):
    info = ZipInfo(PREFIX + "unsafe")
    info.create_system = 3
    info.external_attr = (kind | 0o777) << 16
    with pytest.raises(GitHubSubpathError, match="unsafe entry"):
        source(exclude=(".*",)).sync(
            tmp_path / "target", client=ArchiveClient([(info, b"x")])
        )


@pytest.mark.parametrize("reverse", [False, True])
def test_excluded_file_ancestor_conflicts_are_rejected(tmp_path, reverse):
    entries = [(PREFIX + "parent", b"file"), (PREFIX + "parent/app.py", b"x")]
    if reverse:
        entries.reverse()
    with pytest.raises(GitHubSubpathError, match="conflict"):
        source(exclude=(".*",)).sync(tmp_path / "target", client=ArchiveClient(entries))


def test_excluded_duplicate_is_rejected(tmp_path):
    with pytest.warns(UserWarning, match="Duplicate"):
        client = ArchiveClient([(PREFIX + "a", b"1"), (PREFIX + "a", b"2")])
    with pytest.raises(GitHubSubpathError, match="colliding"):
        source(exclude=(".*",)).sync(tmp_path / "target", client=client)


@pytest.mark.skipif(
    os.path.normcase("A") != os.path.normcase("a"), reason="host is case-sensitive"
)
@pytest.mark.parametrize(
    "names", [("A", "a"), (".COMMIT",), (".ZUU-FILTERS.JSON",), ("DIR", "dir/a")]
)
def test_excluded_host_case_conflicts_are_rejected(tmp_path, names):
    with pytest.raises(GitHubSubpathError):
        source(exclude=(".*",)).sync(
            tmp_path / "target",
            client=ArchiveClient([(PREFIX + n, b"x") for n in names]),
        )


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable modes unavailable")
def test_filtered_executable_bits(tmp_path):
    info = ZipInfo(PREFIX + "nested/run.sh")
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o755) << 16
    target = tmp_path / "target"
    source(include=(r"\.sh$",)).sync(
        target, client=ArchiveClient([(info, b"#!/bin/sh\n")])
    )
    assert (target / "nested/run.sh").stat().st_mode & stat.S_IXUSR


def test_filter_cache_transitions(tmp_path):
    target = tmp_path / "target"
    client = ArchiveClient()
    assert source().sync(target, client=client).changed
    assert source(include=(r"\.py$",)).sync(target, client=client).changed
    assert files(target) == {"app.py", "tests/test_app.py"}
    assert source(include=(r"\.md$",)).sync(target, client=client).changed
    assert files(target) == {"README.md"}
    assert (
        source(include=(r"\.md$",), exclude=("README",))
        .sync(target, client=client)
        .changed
    )
    assert files(target) == set()
    assert source().sync(target, client=client).changed
    assert files(target) == FILES
    assert not (target / MARKER).exists()
    assert not source().sync(target).changed


def test_order_duplicates_and_local_edits_do_not_invalidate_cache(
    tmp_path, monkeypatch
):
    target = tmp_path / "target"
    source(include=(r"\.py$", r"\.md$"), exclude=("^tests/", "draft")).sync(
        target, client=ArchiveClient()
    )
    metadata = json.loads((target / MARKER).read_text())
    assert metadata == {
        "version": 1,
        "include": [r"\.md$", r"\.py$"],
        "exclude": ["^tests/", "draft"],
    }
    (target / "app.py").unlink()
    (target / "README.md").write_bytes(b"local edit")
    (target / "local").write_bytes(b"addition")

    def no_client():
        pytest.fail("pinned cache hit must not instantiate a client")

    monkeypatch.setattr("zuu.case12._default_client", no_client)
    assert (
        not source(
            include=(r"\.md$", r"\.py$", r"\.py$"),
            exclude=("draft", "^tests/", "draft"),
        )
        .sync(target)
        .changed
    )
    assert not (target / "app.py").exists()
    assert (target / "README.md").read_bytes() == b"local edit"
    assert (target / "local").exists()


def test_filtered_branch_is_resolved_before_cache_hit(tmp_path):
    target = tmp_path / "target"
    client = ArchiveClient()
    selected = GitHubSubpath(
        "org", "repo", "templates/python", branch="main", include=(r"\.py$",)
    )
    selected.sync(target, client=client)
    assert not selected.sync(target, client=client).changed
    assert client.resolutions == [("org", "repo", "main")] * 2
    assert len(client.downloads) == 1


@pytest.mark.parametrize(
    "payload",
    [
        None,
        "{",
        "[]",
        '{"version": 2, "include": [], "exclude": []}',
        '{"version": true, "include": [], "exclude": []}',
        '{"version": 1, "include": "x", "exclude": []}',
        '{"version": 1, "include": [4], "exclude": []}',
        '{"version": 1, "include": ["["], "exclude": []}',
        '{"version": 1, "include": [], "exclude": [], "extra": 1}',
        '{"version": 1}',
    ],
)
def test_invalid_metadata_refreshes(tmp_path, payload):
    target = tmp_path / "target"
    client = ArchiveClient()
    selected = source(include=(r"\.py$",))
    selected.sync(target, client=client)
    marker = target / MARKER
    if payload is None:
        marker.unlink()
    else:
        marker.write_text(payload)
    assert selected.sync(target, client=client).changed
    assert len(client.downloads) == 2


@pytest.mark.parametrize("filtered", [False, True])
@pytest.mark.parametrize(
    "failure", ["directory", "unreadable", "junction", "symlink", "unicode"]
)
def test_unusable_metadata_is_not_a_legacy_cache_hit(
    tmp_path, monkeypatch, filtered, failure
):
    target = tmp_path / "target"
    client = ArchiveClient()
    source().sync(target, client=client)
    marker = target / MARKER
    marker.write_text('{"version": 1, "include": [], "exclude": []}')
    if failure == "directory":
        marker.unlink()
        marker.mkdir()
    elif failure == "unicode":
        marker.write_bytes(b"\xff")
    elif failure == "unreadable":
        original = Path.read_text

        def unreadable(path, *args, **kwargs):
            if path == marker:
                raise PermissionError("denied")
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", unreadable)
    elif failure == "junction":
        original = Path.is_junction
        monkeypatch.setattr(
            Path, "is_junction", lambda path: path == marker or original(path)
        )
    else:
        marker.unlink()
        try:
            marker.symlink_to(tmp_path / "missing-metadata")
        except OSError as error:
            pytest.skip(f"symlinks unavailable: {error}")
    selected = source(include=(r"\.py$",)) if filtered else source()
    assert selected.sync(target, client=client).changed
    assert len(client.downloads) == 2


@pytest.mark.parametrize("failure", ["metadata", "install", "archive"])
def test_filtered_failures_preserve_old_content_and_metadata(
    tmp_path, monkeypatch, failure
):
    target = tmp_path / "target"
    source(include=(r"\.py$",)).sync(target, client=ArchiveClient())
    before = {
        p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()
    }
    client = ArchiveClient()
    if failure == "metadata":
        original = Path.write_text

        def fail_metadata(path, *args, **kwargs):
            if path.name == MARKER and path.parent.name == "content":
                raise OSError("metadata staging failed")
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", fail_metadata)
    elif failure == "install":
        original = Path.replace

        def fail_install(path, destination):
            if path.name == "content":
                raise OSError("install failed")
            return original(path, destination)

        monkeypatch.setattr(Path, "replace", fail_install)
    else:
        client.archive = b"invalid zip"
    with pytest.raises(GitHubSubpathError):
        source(include=(r"\.md$",)).sync(target, client=client)
    after = {
        p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()
    }
    assert after == before
    assert not list(tmp_path.glob(".target.zuu-*"))
