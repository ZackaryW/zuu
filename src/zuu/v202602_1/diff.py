"""Helpers for replaying local exported-tree changes onto another repository commit.

The caller is responsible for making cache mutation safe. In practice that means:
- restore the cache to its tracked branch before starting,
- run the diff/apply flow while holding a cache lock,
- restore and clean the cache again before returning.
"""

from pathlib import Path
import shutil
import tempfile
from typing import Callable, Literal

from .git import get_current_commit
from .git import run_git_command


ConflictResolution = Literal["raise", "ours", "theirs"]


def _raise_for_failed_diff_command(
	repository_path: Path,
	command_description: str,
	result,
) -> None:
	if result.returncode == 0:
		return

	message = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
	raise RuntimeError(f"{command_description} failed for {repository_path}: {message}")


def _pathspec_args(subpath: str | None) -> list[str]:
	return [] if subpath is None else ["--", subpath]


def _list_git_paths(repository_path: Path, args: list[str]) -> list[Path]:
	result = run_git_command(repository_path, args)
	_raise_for_failed_diff_command(repository_path, f"git {' '.join(args)}", result)
	return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _create_snapshot_commit(repository_path: Path, subpath: str | None) -> str:
	"""Create a temporary commit that captures the overlaid local tree state.

	The caller is expected to have already checked out ``base_commit`` or another
	desired starting point before invoking this helper.
	"""

	add_args = ["add", "-A", *_pathspec_args(subpath)]
	add_result = run_git_command(repository_path, add_args)
	_raise_for_failed_diff_command(repository_path, f"git {' '.join(add_args)}", add_result)

	commit_result = run_git_command(
		repository_path,
		[
			"-c",
			"user.name=zuu exportDiff",
			"-c",
			"user.email=zuu-exportdiff@example.invalid",
			"commit",
			"-m",
			"zuu exportDiff snapshot",
		],
	)
	_raise_for_failed_diff_command(repository_path, "git commit -m zuu exportDiff snapshot", commit_result)
	return get_current_commit(repository_path)


def _default_diff_path(destination: Path) -> Path:
	return destination.parent / f"{destination.name}.diff"


def _write_diff_file(patch_path: Path, patch_text: str) -> Path:
	patch_path.parent.mkdir(parents=True, exist_ok=True)
	with patch_path.open("w", encoding="utf-8", newline="\n") as diff_file:
		diff_file.write(patch_text)
	return patch_path


def _remove_path(path: Path) -> None:
	if not path.exists():
		return

	if path.is_dir():
		shutil.rmtree(path)
		return

	path.unlink()


def _copy_path(source_path: Path, destination_path: Path) -> None:
	if source_path.is_dir():
		shutil.copytree(source_path, destination_path)
		return

	destination_path.parent.mkdir(parents=True, exist_ok=True)
	shutil.copy2(source_path, destination_path)


def _replace_directory_contents(source_dir: Path, destination_dir: Path, preserved_names: set[str]) -> None:
	destination_dir.mkdir(parents=True, exist_ok=True)
	for child in destination_dir.iterdir():
		if child.name in preserved_names:
			continue
		_remove_path(child)

	for child in source_dir.iterdir():
		if child.name in preserved_names:
			continue
		_copy_path(child, destination_dir / child.name)


def _overlay_local_tree(local_source: Path, repository_path: Path, subpath: str | None) -> None:
	if not local_source.exists():
		raise FileNotFoundError(f"Local export source does not exist: {local_source}")

	if subpath is None:
		if not local_source.is_dir():
			raise ValueError("path must be a directory when target.subpath is None")

		_replace_directory_contents(local_source, repository_path, preserved_names={".git"})
		return

	target_path = repository_path / subpath
	_remove_path(target_path)

	if local_source.is_dir():
		target_path.mkdir(parents=True, exist_ok=True)
		for child in local_source.iterdir():
			_copy_path(child, target_path / child.name)
		return

	target_path.parent.mkdir(parents=True, exist_ok=True)
	shutil.copy2(local_source, target_path)


def _apply_patch(
	repository_path: Path,
	patch_path: Path,
	conflict_resolution: ConflictResolution,
) -> None:
	result = run_git_command(
		repository_path,
		["apply", "--whitespace=nowarn", "--3way", "--index", str(patch_path)],
	)
	if result.returncode == 0:
		return

	if conflict_resolution == "raise":
		_raise_for_failed_diff_command(repository_path, "git apply --3way --index", result)

	conflicted_paths = _list_git_paths(repository_path, ["diff", "--name-only", "--diff-filter=U"])
	if not conflicted_paths:
		_raise_for_failed_diff_command(repository_path, "git apply --3way --index", result)

	checkout_result = run_git_command(
		repository_path,
		["checkout", f"--{conflict_resolution}", "--", *(str(path) for path in conflicted_paths)],
	)
	_raise_for_failed_diff_command(repository_path, f"git checkout --{conflict_resolution}", checkout_result)

	add_result = run_git_command(
		repository_path,
		["add", "--", *(str(path) for path in conflicted_paths)],
	)
	_raise_for_failed_diff_command(repository_path, "git add", add_result)


def _export_diff_impl(
	local_source: Path,
	cache_path: Path,
	destination: Path,
	base_commit: str,
	target_commit: str,
	subpath: str | None,
	conflict_resolution: ConflictResolution,
	copy_export_source: Callable[[Path, Path], None],
	persisted_diff_path: Path | None,
) -> Path | None:
	if conflict_resolution not in {"raise", "ours", "theirs"}:
		raise ValueError("conflict_resolution must be one of: raise, ours, theirs")

	checkout_result = run_git_command(cache_path, ["checkout", "--force", base_commit])
	_raise_for_failed_diff_command(cache_path, f"git checkout --force {base_commit}", checkout_result)

	_overlay_local_tree(local_source, cache_path, subpath)
	snapshot_commit = _create_snapshot_commit(cache_path, subpath)

	with tempfile.TemporaryDirectory() as temp_dir_name:
		temp_dir = Path(temp_dir_name)
		patch_result = run_git_command(
			cache_path,
			["diff", "--binary", "--full-index", base_commit, snapshot_commit, *_pathspec_args(subpath)],
		)
		_raise_for_failed_diff_command(cache_path, "git diff --binary", patch_result)

		patch_path = temp_dir / "changes.diff" if persisted_diff_path is None else persisted_diff_path
		patch_path = _write_diff_file(patch_path, patch_result.stdout)

		reset_result = run_git_command(cache_path, ["reset", "--hard", target_commit])
		_raise_for_failed_diff_command(cache_path, f"git reset --hard {target_commit}", reset_result)

		clean_result = run_git_command(cache_path, ["clean", "-fd"])
		_raise_for_failed_diff_command(cache_path, "git clean -fd", clean_result)

		if patch_path.stat().st_size > 0:
			_apply_patch(cache_path, patch_path, conflict_resolution)

		source_path = cache_path if subpath is None else cache_path / subpath
		if not source_path.exists():
			if destination.exists():
				_remove_path(destination)
		else:
			copy_export_source(source_path, destination)

		return persisted_diff_path


def export_diff(
	local_source: Path,
	cache_path: Path,
	destination: Path,
	base_commit: str,
	target_commit: str,
	subpath: str | None,
	conflict_resolution: ConflictResolution,
	copy_export_source: Callable[[Path, Path], None],
) -> None:
	"""Replay local exported-tree changes from ``base_commit`` onto ``target_commit``.

	The algorithm is:
	1. Checkout ``base_commit`` in the cache.
	2. Overlay the plain local tree from ``local_source`` onto that checkout.
	3. Snapshot those overlaid changes in a temporary commit.
	4. Generate a git diff from ``base_commit`` to that snapshot.
	5. Reset the cache to ``target_commit``.
	6. Apply the diff with ``git apply --3way``.
	7. Copy the resulting files to ``destination`` without the ``.git`` directory.

	The caller must restore the cache branch, commit, and cleanliness after this call.
	"""

	_export_diff_impl(
		local_source=local_source,
		cache_path=cache_path,
		destination=destination,
		base_commit=base_commit,
		target_commit=target_commit,
		subpath=subpath,
		conflict_resolution=conflict_resolution,
		copy_export_source=copy_export_source,
		persisted_diff_path=None,
	)


def export_diff_and_return_path(
	local_source: Path,
	cache_path: Path,
	destination: Path,
	base_commit: str,
	target_commit: str,
	subpath: str | None,
	conflict_resolution: ConflictResolution,
	copy_export_source: Callable[[Path, Path], None],
	diff_path: Path | None = None,
) -> Path:
	"""Run :func:`export_diff` and persist the generated patch file.

	Returns the path to the saved diff file. When ``diff_path`` is omitted, the file
	is written next to ``destination`` using ``<destination>.diff``.
	"""

	persisted_diff_path = diff_path if diff_path is not None else _default_diff_path(destination)
	result = _export_diff_impl(
		local_source=local_source,
		cache_path=cache_path,
		destination=destination,
		base_commit=base_commit,
		target_commit=target_commit,
		subpath=subpath,
		conflict_resolution=conflict_resolution,
		copy_export_source=copy_export_source,
		persisted_diff_path=persisted_diff_path,
	)
	assert result is not None
	return result