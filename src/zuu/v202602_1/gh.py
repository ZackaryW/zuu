from dataclasses import dataclass
from functools import cache
import json
from pathlib import Path
import shutil
import subprocess


@dataclass(frozen=True)
class GitHubRepo:
	name: str
	description: str
	updated_at: str


def run_command(command: str, args: list[str]) -> subprocess.CompletedProcess[str]:
	return subprocess.run(
		[command, *args],
		capture_output=True,
		check=False,
		text=True,
	)


@cache
def is_gh_available() -> bool:
	return shutil.which("gh") is not None


def parse_gh_auth_status(output: str) -> bool:
	normalized_output = output.casefold()

	if not normalized_output.strip():
		return False

	if any(
		marker in normalized_output
		for marker in (
			"not logged in",
			"not logged into any github hosts",
			"failed to log in",
			"authentication failed",
			"token is invalid",
			"token has expired",
		)
	):
		return False

	return any(
		marker in normalized_output
		for marker in (
			"logged in to",
			"active account: true",
		)
	)


@cache
def is_gh_logged_in() -> bool:
	if not is_gh_available():
		return False

	result = run_command("gh", ["auth", "status"])
	combined_output = "\n".join(part for part in (result.stdout, result.stderr) if part)
	return parse_gh_auth_status(combined_output)


def parse_repository_search_output(output: str) -> list[GitHubRepo]:
	repositories = json.loads(output)
	return [
		GitHubRepo(
			name=repository["name"],
			description=repository.get("description") or "",
			updated_at=repository["updatedAt"],
		)
		for repository in repositories
	]


def search_repositories(query: str, owner: str) -> list[GitHubRepo]:
	result = run_command(
		"gh",
		["search", "repos", query, f"--owner={owner}", "--json", "updatedAt,description,name"],
	)
	return parse_repository_search_output(result.stdout)


def clone_repository(
	repository: str,
	destination: Path | str,
	branch: str | None = None,
) -> subprocess.CompletedProcess[str]:
	args = ["repo", "clone", repository, str(destination)]
	if branch is not None:
		args.extend(["--", "--branch", branch, "--single-branch"])

	return run_command("gh", args)
