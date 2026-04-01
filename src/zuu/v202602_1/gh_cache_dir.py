import json
from pathlib import Path
import shutil
import subprocess
import time

from .gh import clone_repository
from .git import checkout_commit
from .git import get_current_commit


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
				return cache_path

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

	def export(self, path: str, repo: str, branch: str | None = None, subpath: str | None = None) -> None:
		destination = Path(path).expanduser()
		source_root = self.resolve_cached_repo_path(repo, branch)
		source_path = source_root if subpath is None else source_root / subpath

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

	def exportCommit(
		self,
		path: str,
		commit: str,
		repo: str,
		branch: str | None = None,
		subpath: str | None = None,
	) -> None:
		cache_path = self.resolve_cached_repo_path(repo, branch)
		original_commit = get_current_commit(cache_path)

		checkout_commit(cache_path, commit)
		try:
			self.export(path, repo, branch=branch, subpath=subpath)
		finally:
			checkout_commit(cache_path, original_commit)
	



