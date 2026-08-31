from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from zuu.case12 import GitHubSubpath, GitHubSubpathError, GitHubSyncResult


FIRST = "1" * 40
SECOND = "2" * 40


def archive_bytes(*, content: bytes = b"print('hello')\n") -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("org-repo-abcd/templates/python/main.py", content)
        archive.writestr("org-repo-abcd/templates/python/nested/data.txt", b"data")
        archive.writestr("org-repo-abcd/unrelated.txt", b"ignored")
    return stream.getvalue()


class FakeClient:
    def __init__(
        self,
        *,
        commit: str = FIRST,
        archive: bytes | None = None,
        failure: Exception | None = None,
    ) -> None:
        self.commit = commit
        self.archive = archive if archive is not None else archive_bytes()
        self.failure = failure
        self.resolutions: list[tuple[str, str, str | None]] = []
        self.downloads: list[tuple[str, str, str]] = []

    def resolve_commit(
        self,
        owner: str,
        repository: str,
        branch: str | None,
    ) -> str:
        self.resolutions.append((owner, repository, branch))
        return self.commit

    def download_archive(
        self,
        owner: str,
        repository: str,
        commit: str,
        destination: Path,
    ) -> None:
        self.downloads.append((owner, repository, commit))
        if self.failure is not None:
            raise self.failure
        destination.write_bytes(self.archive)


def test_default_branch_sync_materializes_only_the_selected_directory(
    tmp_path: Path,
) -> None:
    client = FakeClient()
    source = GitHubSubpath("org", "repo", "templates/python")
    target = tmp_path / "target"

    result = source.sync(target, client=client)

    assert result == GitHubSyncResult(target.absolute(), FIRST, True)
    assert client.resolutions == [("org", "repo", None)]
    assert client.downloads == [("org", "repo", FIRST)]
    assert (target / "main.py").read_bytes() == b"print('hello')\n"
    assert (target / "nested" / "data.txt").read_bytes() == b"data"
    assert (target / ".commit").read_text(encoding="ascii") == FIRST + "\n"
    assert not (target / "unrelated.txt").exists()


def test_branch_override_is_resolved_before_download(tmp_path: Path) -> None:
    client = FakeClient(commit=SECOND)
    source = GitHubSubpath(
        "org",
        "repo",
        "templates/python",
        branch="feature/templates",
    )

    result = source.sync(tmp_path / "target", client=client)

    assert result.commit == SECOND
    assert client.resolutions == [("org", "repo", "feature/templates")]


def test_matching_explicit_commit_skips_without_a_client(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / ".commit").write_text(FIRST + "\n", encoding="ascii")
    (target / "locally-edited.txt").write_text("preserved", encoding="utf-8")
    source = GitHubSubpath("org", "repo", "templates/python", commit=FIRST)

    result = source.sync(target)

    assert result == GitHubSyncResult(target.absolute(), FIRST, False)
    assert (target / "locally-edited.txt").read_text(encoding="utf-8") == "preserved"


def test_matching_resolved_branch_skips_archive_download(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / ".commit").write_text(FIRST, encoding="ascii")
    client = FakeClient(commit=FIRST)

    result = GitHubSubpath(
        "org",
        "repo",
        "templates/python",
        branch="main",
    ).sync(target, client=client)

    assert result.changed is False
    assert client.resolutions == [("org", "repo", "main")]
    assert client.downloads == []


def test_changed_commit_replaces_the_complete_owned_target(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / ".commit").write_text(FIRST, encoding="ascii")
    (target / "local.txt").write_text("not protected", encoding="utf-8")
    client = FakeClient(commit=SECOND, archive=archive_bytes(content=b"second\n"))

    result = GitHubSubpath(
        "org",
        "repo",
        "templates/python",
        branch="main",
    ).sync(target, client=client)

    assert result.changed is True
    assert not (target / "local.txt").exists()
    assert (target / "main.py").read_bytes() == b"second\n"
    assert (target / ".commit").read_text(encoding="ascii") == SECOND + "\n"


def test_missing_or_invalid_marker_does_not_claim_a_cache_hit(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / ".commit").write_text("not-a-commit", encoding="ascii")
    client = FakeClient(commit=FIRST)

    result = GitHubSubpath(
        "org",
        "repo",
        "templates/python",
        commit=FIRST,
    ).sync(target, client=client)

    assert result.changed is True
    assert client.resolutions == []
    assert client.downloads == [("org", "repo", FIRST)]


def test_download_failure_preserves_the_previous_target(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / ".commit").write_text(FIRST + "\n", encoding="ascii")
    (target / "previous.txt").write_text("previous", encoding="utf-8")
    client = FakeClient(commit=SECOND, failure=OSError("offline"))

    with pytest.raises(GitHubSubpathError, match="download"):
        GitHubSubpath(
            "org",
            "repo",
            "templates/python",
            branch="main",
        ).sync(target, client=client)

    assert (target / ".commit").read_text(encoding="ascii") == FIRST + "\n"
    assert (target / "previous.txt").read_text(encoding="utf-8") == "previous"


def test_invalid_archive_preserves_the_previous_target(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / ".commit").write_text(FIRST + "\n", encoding="ascii")
    (target / "previous.txt").write_text("previous", encoding="utf-8")
    client = FakeClient(commit=SECOND, archive=b"not a ZIP archive")

    with pytest.raises(GitHubSubpathError, match="materialized"):
        GitHubSubpath(
            "org",
            "repo",
            "templates/python",
            branch="main",
        ).sync(target, client=client)

    assert (target / ".commit").read_text(encoding="ascii") == FIRST + "\n"
    assert (target / "previous.txt").read_text(encoding="utf-8") == "previous"


def test_install_failure_restores_the_previous_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / ".commit").write_text(FIRST, encoding="ascii")
    (target / "previous.txt").write_text("previous", encoding="utf-8")
    original_replace = Path.replace

    def fail_staged_replace(path: Path, destination: Path) -> Path:
        if path.name == "content":
            raise OSError("install failed")
        return original_replace(path, destination)

    monkeypatch.setattr(Path, "replace", fail_staged_replace)

    with pytest.raises(GitHubSubpathError, match="synchronize target"):
        GitHubSubpath(
            "org",
            "repo",
            "templates/python",
            commit=SECOND,
        ).sync(target, client=FakeClient(commit=SECOND))

    assert (target / ".commit").read_text(encoding="ascii") == FIRST
    assert (target / "previous.txt").read_text(encoding="utf-8") == "previous"


def test_invalid_resolved_commit_is_rejected_before_download(tmp_path: Path) -> None:
    client = FakeClient(commit="short")

    with pytest.raises(GitHubSubpathError, match="40-character"):
        GitHubSubpath("org", "repo", "templates/python").sync(
            tmp_path / "target",
            client=client,
        )

    assert client.downloads == []
