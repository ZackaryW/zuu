from __future__ import annotations

import os
import stat
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

from zuu.case12 import GitHubSubpath, GitHubSubpathError

FIRST = "1" * 40


class FakeClient:
    def __init__(self, archive: bytes) -> None:
        self.archive = archive

    def resolve_commit(
        self,
        owner: str,
        repository: str,
        branch: str | None,
    ) -> str:
        return FIRST

    def download_archive(
        self,
        owner: str,
        repository: str,
        commit: str,
        destination: Path,
    ) -> None:
        destination.write_bytes(self.archive)


def make_archive(entries: list[tuple[ZipInfo | str, bytes]]) -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return stream.getvalue()


def sync_archive(tmp_path: Path, archive: bytes) -> Path:
    target = tmp_path / "target"
    GitHubSubpath(
        "org",
        "repo",
        "templates/python",
        commit=FIRST,
    ).sync(target, client=FakeClient(archive))
    return target


def test_missing_source_directory_is_rejected(tmp_path: Path) -> None:
    archive = make_archive([("root/other/file.txt", b"other")])

    with pytest.raises(GitHubSubpathError, match="not found"):
        sync_archive(tmp_path, archive)


def test_file_source_is_rejected(tmp_path: Path) -> None:
    archive = make_archive([("root/templates/python", b"file")])

    with pytest.raises(GitHubSubpathError, match="not a directory"):
        sync_archive(tmp_path, archive)


@pytest.mark.parametrize(
    "name",
    [
        "root/templates/python/../outside.txt",
        "/root/templates/python/outside.txt",
    ],
)
def test_unsafe_archive_paths_are_rejected(tmp_path: Path, name: str) -> None:
    archive = make_archive([(name, b"unsafe")])

    with pytest.raises(GitHubSubpathError, match="unsafe path"):
        sync_archive(tmp_path, archive)


def test_multiple_archive_roots_are_rejected(tmp_path: Path) -> None:
    archive = make_archive(
        [
            ("first/templates/python/a.txt", b"a"),
            ("second/templates/python/b.txt", b"b"),
        ]
    )

    with pytest.raises(GitHubSubpathError, match="one repository root"):
        sync_archive(tmp_path, archive)


def test_selected_symlink_is_rejected(tmp_path: Path) -> None:
    link = ZipInfo("root/templates/python/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    archive = make_archive([(link, b"../../outside")])

    with pytest.raises(GitHubSubpathError, match="unsafe entry"):
        sync_archive(tmp_path, archive)


@pytest.mark.parametrize(
    "name",
    [
        "root/templates/python/.commit",
        "root/templates/python/.commit/source.txt",
    ],
)
def test_reserved_top_level_commit_path_is_rejected(
    tmp_path: Path,
    name: str,
) -> None:
    archive = make_archive([(name, b"source marker")])

    with pytest.raises(GitHubSubpathError, match="reserved"):
        sync_archive(tmp_path, archive)


def test_colliding_archive_entries_are_rejected(tmp_path: Path) -> None:
    with pytest.warns(UserWarning, match="Duplicate name"):
        archive = make_archive(
            [
                ("root/templates/python/value.txt", b"first"),
                ("root/templates/python/value.txt", b"second"),
            ]
        )

    with pytest.raises(GitHubSubpathError, match="colliding"):
        sync_archive(tmp_path, archive)


def test_executable_mode_is_preserved(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("Windows does not expose POSIX executable mode preservation")
    executable = ZipInfo("root/templates/python/run.sh")
    executable.create_system = 3
    executable.external_attr = (stat.S_IFREG | 0o755) << 16
    archive = make_archive([(executable, b"#!/bin/sh\n")])

    target = sync_archive(tmp_path, archive)

    assert (target / "run.sh").stat().st_mode & stat.S_IXUSR
