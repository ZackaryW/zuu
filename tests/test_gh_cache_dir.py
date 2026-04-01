import subprocess

import json

from zuu.v202602_1.gh_cache_dir import GhCacheDir


def test_ensure_clones_missing_repository_directory(monkeypatch, tmp_path) -> None:
	cache_dir = GhCacheDir(tmp_path / "cache", 60)
	clone_calls: list[tuple[str, str, str | None]] = []

	monkeypatch.setattr(
		"zuu.v202602_1.gh_cache_dir.clone_repository",
		lambda repository, destination, branch=None: clone_calls.append((repository, str(destination), branch))
		or subprocess.CompletedProcess(args=["gh"], returncode=0, stdout="", stderr=""),
	)
	monkeypatch.setattr(
		GhCacheDir,
		"_run_git_command",
		lambda self, cache_path, args: (_ for _ in ()).throw(AssertionError("git pull should not run during clone")),
	)

	result = cache_dir.ensure("octocat/hello-world", branch="main", current_time=100.0)

	assert result == tmp_path / "cache" / "octocat_hello-world_main"
	assert clone_calls == [("octocat/hello-world", str(tmp_path / "cache" / "octocat_hello-world_main"), "main")]
	assert json.loads((tmp_path / "cache" / "index.json").read_text(encoding="utf-8")) == {
		"octocat_hello-world_main": {
			"branch": "main",
			"last_updated_at": 100.0,
			"repository": "octocat/hello-world",
		}
	}


def test_ensure_pulls_existing_directory_when_due(monkeypatch, tmp_path) -> None:
	cache_dir = GhCacheDir(tmp_path / "cache", 60)
	cache_path = tmp_path / "cache" / "octocat_hello-world_main"
	cache_dir.path.mkdir()
	cache_path.mkdir()
	(tmp_path / "cache" / "index.json").write_text(
		json.dumps(
			{
				"octocat_hello-world_main": {
					"repository": "octocat/hello-world",
					"branch": "main",
					"last_updated_at": 100.0,
				}
			}
		),
		encoding="utf-8",
	)
	git_calls: list[tuple[str, list[str]]] = []

	monkeypatch.setattr(
		GhCacheDir,
		"_run_git_command",
		lambda self, path, args: git_calls.append((str(path), args))
		or subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr=""),
	)

	first_result = cache_dir.ensure("octocat/hello-world", branch="main", current_time=100.0)
	second_result = cache_dir.ensure("octocat/hello-world", branch="main", current_time=120.0)
	third_result = cache_dir.ensure("octocat/hello-world", branch="main", current_time=160.0)

	assert first_result == cache_path
	assert second_result == cache_path
	assert third_result == cache_path
	assert git_calls == [(str(cache_path), ["pull", "--ff-only"])]
	assert json.loads((tmp_path / "cache" / "index.json").read_text(encoding="utf-8"))["octocat_hello-world_main"]["last_updated_at"] == 160.0


def test_is_due_for_check_uses_minimum_interval(tmp_path) -> None:
	cache_dir = GhCacheDir(tmp_path / "cache", 30)
	cache_dir.path.mkdir()
	(tmp_path / "cache" / "index.json").write_text(
		json.dumps(
			{
				"octocat_hello-world_main": {
					"repository": "octocat/hello-world",
					"branch": "main",
					"last_updated_at": 100.0,
				}
			}
		),
		encoding="utf-8",
	)

	assert cache_dir.is_due_for_check("octocat/hello-world", "main", 129.0) is False
	assert cache_dir.is_due_for_check("octocat/hello-world", "main", 130.0) is True


def test_ensure_raises_when_git_pull_fails(monkeypatch, tmp_path) -> None:
	cache_dir = GhCacheDir(tmp_path / "cache", 1)
	cache_path = tmp_path / "cache" / "octocat_hello-world_main"
	cache_dir.path.mkdir()
	cache_path.mkdir()
	(tmp_path / "cache" / "index.json").write_text(
		json.dumps(
			{
				"octocat_hello-world_main": {
					"repository": "octocat/hello-world",
					"branch": "main",
					"last_updated_at": 0.0,
				}
			}
		),
		encoding="utf-8",
	)

	monkeypatch.setattr(
		GhCacheDir,
		"_run_git_command",
		lambda self, path, args: subprocess.CompletedProcess(
			args=["git", *args],
			returncode=1,
			stdout="",
			stderr="merge conflict",
		),
	)

	try:
		cache_dir.ensure("octocat/hello-world", branch="main", current_time=10.0)
		raise AssertionError("ensure should raise when git pull fails")
	except RuntimeError as exc:
		assert "merge conflict" in str(exc)


def test_cache_folder_name_uses_org_repo_branch_format(tmp_path) -> None:
	cache_dir = GhCacheDir(tmp_path / "cache", 60)

	assert cache_dir.cache_folder_name("octocat/hello-world", "release/2026") == "octocat_hello-world_release_2026"


def test_resolve_cached_repo_path_accepts_short_repo_name_with_first_match(tmp_path) -> None:
	cache_dir = GhCacheDir(tmp_path / "cache", 60)
	cache_dir.path.mkdir()
	(cache_dir.path / "firstorg_shared_main").mkdir()
	(cache_dir.path / "secondorg_shared_release").mkdir()
	cache_dir.index_path.write_text(
		json.dumps(
			{
				"firstorg_shared_main": {
					"repository": "firstorg/shared",
					"branch": "main",
					"last_updated_at": 100.0,
				},
				"secondorg_shared_release": {
					"repository": "secondorg/shared",
					"branch": "release",
					"last_updated_at": 200.0,
				},
			}
		),
		encoding="utf-8",
	)

	assert cache_dir.resolve_cached_repo_path("shared") == cache_dir.path / "firstorg_shared_main"


def test_resolve_cached_repo_path_uses_full_repo_and_branch_when_provided(tmp_path) -> None:
	cache_dir = GhCacheDir(tmp_path / "cache", 60)
	cache_dir.path.mkdir()
	(cache_dir.path / "octocat_hello-world_main").mkdir()
	(cache_dir.path / "octocat_hello-world_release_2026").mkdir()
	cache_dir.index_path.write_text(
		json.dumps(
			{
				"octocat_hello-world_main": {
					"repository": "octocat/hello-world",
					"branch": "main",
					"last_updated_at": 100.0,
				},
				"octocat_hello-world_release_2026": {
					"repository": "octocat/hello-world",
					"branch": "release/2026",
					"last_updated_at": 200.0,
				},
			}
		),
		encoding="utf-8",
	)

	assert cache_dir.resolve_cached_repo_path("octocat/hello-world", "release/2026") == (
		cache_dir.path / "octocat_hello-world_release_2026"
	)


def test_export_copies_entire_repository_without_git_directory(tmp_path) -> None:
	cache_dir = GhCacheDir(tmp_path / "cache", 60)
	cache_path = cache_dir.path / "octocat_hello-world_main"
	cache_path.mkdir(parents=True)
	(cache_path / ".git").mkdir()
	(cache_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
	(cache_path / "README.md").write_text("hello\n", encoding="utf-8")
	(cache_path / "src").mkdir()
	(cache_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
	cache_dir.index_path.write_text(
		json.dumps(
			{
				"octocat_hello-world_main": {
					"repository": "octocat/hello-world",
					"branch": "main",
					"last_updated_at": 100.0,
				}
			}
		),
		encoding="utf-8",
	)
	output_path = tmp_path / "exported"

	cache_dir.export(str(output_path), "hello-world")

	assert (output_path / "README.md").read_text(encoding="utf-8") == "hello\n"
	assert (output_path / "src" / "app.py").read_text(encoding="utf-8") == "print('hi')\n"
	assert (output_path / ".git").exists() is False


def test_export_copies_only_selected_subpath(tmp_path) -> None:
	cache_dir = GhCacheDir(tmp_path / "cache", 60)
	cache_path = cache_dir.path / "octocat_hello-world_main"
	(cache_path / "src").mkdir(parents=True)
	(cache_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
	(cache_path / "README.md").write_text("hello\n", encoding="utf-8")
	cache_dir.index_path.write_text(
		json.dumps(
			{
				"octocat_hello-world_main": {
					"repository": "octocat/hello-world",
					"branch": "main",
					"last_updated_at": 100.0,
				}
			}
		),
		encoding="utf-8",
	)
	output_path = tmp_path / "exported-src"

	cache_dir.export(str(output_path), "octocat/hello-world", subpath="src")

	assert (output_path / "app.py").read_text(encoding="utf-8") == "print('hi')\n"
	assert (output_path / "README.md").exists() is False


def test_export_commit_checks_out_target_then_restores(monkeypatch, tmp_path) -> None:
	cache_dir = GhCacheDir(tmp_path / "cache", 60)
	cache_path = cache_dir.path / "octocat_hello-world_main"
	cache_path.mkdir(parents=True)
	cache_dir.index_path.write_text(
		json.dumps(
			{
				"octocat_hello-world_main": {
					"repository": "octocat/hello-world",
					"branch": "main",
					"last_updated_at": 100.0,
				}
			}
		),
		encoding="utf-8",
	)
	call_log: list[tuple[str, str, str]] = []

	monkeypatch.setattr(
		"zuu.v202602_1.gh_cache_dir.get_current_commit",
		lambda path: call_log.append(("get_current_commit", str(path), "")) or "abc123",
	)
	monkeypatch.setattr(
		"zuu.v202602_1.gh_cache_dir.checkout_commit",
		lambda path, commit: call_log.append(("checkout_commit", str(path), commit)),
	)
	monkeypatch.setattr(
		GhCacheDir,
		"export",
		lambda self, path, repo, branch=None, subpath=None: call_log.append(("export", path, repo)),
	)

	cache_dir.exportCommit(str(tmp_path / "out"), "def456", "octocat/hello-world", branch="main")

	assert call_log == [
		("get_current_commit", str(cache_path), ""),
		("checkout_commit", str(cache_path), "def456"),
		("export", str(tmp_path / "out"), "octocat/hello-world"),
		("checkout_commit", str(cache_path), "abc123"),
	]


def test_export_commit_restores_original_commit_when_export_fails(monkeypatch, tmp_path) -> None:
	cache_dir = GhCacheDir(tmp_path / "cache", 60)
	cache_path = cache_dir.path / "octocat_hello-world_main"
	cache_path.mkdir(parents=True)
	cache_dir.index_path.write_text(
		json.dumps(
			{
				"octocat_hello-world_main": {
					"repository": "octocat/hello-world",
					"branch": "main",
					"last_updated_at": 100.0,
				}
			}
		),
		encoding="utf-8",
	)
	call_log: list[tuple[str, str, str]] = []

	monkeypatch.setattr(
		"zuu.v202602_1.gh_cache_dir.get_current_commit",
		lambda path: call_log.append(("get_current_commit", str(path), "")) or "abc123",
	)
	monkeypatch.setattr(
		"zuu.v202602_1.gh_cache_dir.checkout_commit",
		lambda path, commit: call_log.append(("checkout_commit", str(path), commit)),
	)

	def raise_export(self, path, repo, branch=None, subpath=None):
		call_log.append(("export", path, repo))
		raise RuntimeError("export failed")

	monkeypatch.setattr(GhCacheDir, "export", raise_export)

	try:
		cache_dir.exportCommit(str(tmp_path / "out"), "def456", "octocat/hello-world", branch="main")
		raise AssertionError("exportCommit should re-raise export errors")
	except RuntimeError as exc:
		assert str(exc) == "export failed"

	assert call_log == [
		("get_current_commit", str(cache_path), ""),
		("checkout_commit", str(cache_path), "def456"),
		("export", str(tmp_path / "out"), "octocat/hello-world"),
		("checkout_commit", str(cache_path), "abc123"),
	]