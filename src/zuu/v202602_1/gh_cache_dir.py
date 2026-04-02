from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from .diff import ConflictResolution
from .diff import export_diff
from .diff import export_diff_and_return_path
from .gh import clone_repository
from .git import checkout_commit
from .git import get_current_commit


@dataclass(frozen=True)
class CachedRepoTarget:
	"""Select a cached repository plus the optional revision and subpath to export."""

	repo: str
	commit: str | None = None
	branch: str | None = None
	subpath: str | None = None


class GhCacheDir:
	def __init__(self, path_name: Path | str, minimum_ttc_time_to_check_seconds: float) -> None:
		self.path = Path(path_name).expanduser()
		self.minimum_ttc_time_to_check_seconds = float(minimum_ttc_time_to_check_seconds)
		self.index_path = self.path / "index.json"

	def cache_folder_name(self, repository: str, branch: str) -> str:
		owner, repo_name = repository.split("/", maxsplit=1)
		safe_branch = branch.replace("/", "_")
		return f"{owner}_{repo_name}_{safe_branch}"

	def cache_path_for(self, repository: str, branch: str) -> Path:
		return self.path / self.cache_folder_name(repository, branch)

	def is_due_for_check(
		self,
		repository: str,
		branch: str,
		current_time: float | None = None,
	) -> bool:
		if current_time is None:
			current_time = time.time()

		entry = self._read_index().get(self.cache_folder_name(repository, branch))
		if entry is None:
			return True

		last_updated_at = entry.get("last_updated_at")
		if not isinstance(last_updated_at, int | float):
			return True

		return (current_time - float(last_updated_at)) >= self.minimum_ttc_time_to_check_seconds

	def ensure(self, repository: str, branch: str = "main", current_time: float | None = None) -> Path:
		if current_time is None:
			current_time = time.time()

		self.path.mkdir(parents=True, exist_ok=True)
		cache_path = self.cache_path_for(repository, branch)

		if not cache_path.exists():
			result = clone_repository(repository, cache_path, branch=branch)
			self._raise_for_failed_command("gh repo clone", cache_path, result)
			self._write_index_entry(repository, branch, current_time)
			return cache_path

		self._restore_cache_to_branch(cache_path, branch)

		if not self.is_due_for_check(repository, branch, current_time):
			return cache_path

		result = self._run_git_command(cache_path, ["pull", "--ff-only"])
		self._raise_for_failed_command("git pull", cache_path, result)
		self._write_index_entry(repository, branch, current_time)
		return cache_path

	def _read_index(self) -> dict[str, dict[str, object]]:
		if not self.index_path.exists():
			return {}

		return json.loads(self.index_path.read_text(encoding="utf-8"))

	def resolve_cached_repo_path(self, repo: str, branch: str | None = None) -> Path:
		cache_path, _ = self._resolve_cached_repo_details(repo, branch)
		return cache_path

	def _resolve_cached_repo_details(self, repo: str, branch: str | None = None) -> tuple[Path, str]:
		for folder_name, entry in self._read_index().items():
			repository = entry.get("repository")
			entry_branch = entry.get("branch")

			if not isinstance(repository, str) or not isinstance(entry_branch, str):
				continue

			if not self._repository_matches(repo, repository):
				continue

			if branch is not None and entry_branch != branch:
				continue

			cache_path = self.path / folder_name
			if cache_path.exists():
				return cache_path, entry_branch

		raise FileNotFoundError(f"No cached repository matched repo={repo!r} branch={branch!r}")

	def _write_index_entry(self, repository: str, branch: str, current_time: float) -> None:
		index = self._read_index()
		index[self.cache_folder_name(repository, branch)] = {
			"repository": repository,
			"branch": branch,
			"last_updated_at": current_time,
		}
		self.index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")

	def _run_git_command(self, cache_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
		return subprocess.run(
			["git", "-C", str(cache_path), *args],
			capture_output=True,
			check=False,
			input=None,
			text=True,
		)

	def _raise_for_failed_command(
			self,
			command_description: str,
			cache_path: Path,
			result: subprocess.CompletedProcess[str],
	) -> None:
			if result.returncode == 0:
					return

			message = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
			raise RuntimeError(f"{command_description} failed for {cache_path}: {message}")

	def _repository_matches(self, repo_selector: str, repository: str) -> bool:
		if "/" in repo_selector:
			return repo_selector == repository

		return repository.split("/", maxsplit=1)[-1] == repo_selector

	def _lock_path_for(self, cache_path: Path) -> Path:
		return self.path / f"{cache_path.name}.lock"

	def _restore_cache_to_branch(self, cache_path: Path, branch: str, commit: str | None = None) -> None:
		checkout_result = self._run_git_command(cache_path, ["checkout", "--force", branch])
		self._raise_for_failed_command(f"git checkout --force {branch}", cache_path, checkout_result)

		reset_target = commit or branch
		reset_result = self._run_git_command(cache_path, ["reset", "--hard", reset_target])
		self._raise_for_failed_command(f"git reset --hard {reset_target}", cache_path, reset_result)

		clean_result = self._run_git_command(cache_path, ["clean", "-fd"])
		self._raise_for_failed_command("git clean -fd", cache_path, clean_result)

	@contextmanager
	def _mutating_cache(self, cache_path: Path, branch: str):
		lock_path = self._lock_path_for(cache_path)
		try:
			lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
		except FileExistsError as exc:
			raise RuntimeError(f"Cache is already in use: {cache_path}") from exc

		original_commit: str | None = None
		try:
			os.write(lock_fd, str(os.getpid()).encode("utf-8"))
			self._restore_cache_to_branch(cache_path, branch)
			original_commit = get_current_commit(cache_path)
			yield original_commit
		except Exception:
			raise
		finally:
			try:
				if original_commit is not None:
					self._restore_cache_to_branch(cache_path, branch, original_commit)
			finally:
				os.close(lock_fd)
				if lock_path.exists():
					lock_path.unlink()

	def _copy_export_source(self, source_path: Path, destination: Path) -> None:
		if not source_path.exists():
			raise FileNotFoundError(f"Export source does not exist: {source_path}")

		if destination.exists():
			if destination.is_dir():
				shutil.rmtree(destination)
			else:
				destination.unlink()

		ignore = shutil.ignore_patterns(".git")
		if source_path.is_dir():
			shutil.copytree(source_path, destination, ignore=ignore)
			return

		destination.parent.mkdir(parents=True, exist_ok=True)
		shutil.copy2(source_path, destination)

	def export(self, path: str, target: CachedRepoTarget) -> None:
		"""Copy the selected cached repository contents to ``path`` without ``.git``."""

		destination = Path(path).expanduser()
		source_root = self.resolve_cached_repo_path(target.repo, target.branch)
		source_path = source_root if target.subpath is None else source_root / target.subpath
		self._copy_export_source(source_path, destination)

	def exportCommit(self, path: str, target: CachedRepoTarget) -> None:
		"""Temporarily checkout ``target.commit`` in the cached repo, export it, then restore HEAD."""

		if target.commit is None:
			raise ValueError("target.commit is required for exportCommit")

		cache_path, _ = self._resolve_cached_repo_details(target.repo, target.branch)
		original_commit = get_current_commit(cache_path)

		checkout_commit(cache_path, target.commit)
		try:
			self.export(path, target)
		finally:
			checkout_commit(cache_path, original_commit)
	
	def exportDiff(
		self,
		path: str,
		base_commit: str,
		target: CachedRepoTarget,
		conflict_resolution: ConflictResolution = "raise",
	) -> None:
		"""Export local changes from ``base_commit`` replayed onto ``target.commit``.

		This mutates the cached repository transactionally: the cache is restored to its
		tracked branch before the operation starts and restored again before returning.
		The local tree already present at ``path`` is compared against ``base_commit``.
		If ``target.commit`` is omitted, the current cache branch tip is used as the replay target.
		"""

		cache_path, resolved_branch = self._resolve_cached_repo_details(target.repo, target.branch)
		local_path = Path(path).expanduser()
		with self._mutating_cache(cache_path, resolved_branch) as original_commit:
			export_diff(
				local_source=local_path,
				cache_path=cache_path,
				destination=local_path,
				base_commit=base_commit,
				target_commit=target.commit or original_commit,
				subpath=target.subpath,
				conflict_resolution=conflict_resolution,
				copy_export_source=self._copy_export_source,
			)

	def exportDiffAndReturnPath(
		self,
		path: str,
		base_commit: str,
		target: CachedRepoTarget,
		diff_path: str | None = None,
		conflict_resolution: ConflictResolution = "raise",
	) -> Path:
		"""Run :meth:`exportDiff` and return the saved diff file path."""

		cache_path, resolved_branch = self._resolve_cached_repo_details(target.repo, target.branch)
		local_path = Path(path).expanduser()
		with self._mutating_cache(cache_path, resolved_branch) as original_commit:
			return export_diff_and_return_path(
				local_source=local_path,
				cache_path=cache_path,
				destination=local_path,
				base_commit=base_commit,
				target_commit=target.commit or original_commit,
				subpath=target.subpath,
				conflict_resolution=conflict_resolution,
				copy_export_source=self._copy_export_source,
				diff_path=None if diff_path is None else Path(diff_path).expanduser(),
			)