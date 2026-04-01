from pathlib import Path
import subprocess


def run_git_command(repository_path: Path | str, args: list[str]) -> subprocess.CompletedProcess[str]:
	return subprocess.run(
		["git", "-C", str(repository_path), *args],
		capture_output=True,
		check=False,
		text=True,
	)


def _raise_for_failed_git_command(
	repository_path: Path | str,
	command_description: str,
	result: subprocess.CompletedProcess[str],
) -> None:
	if result.returncode == 0:
		return

	message = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
	raise RuntimeError(f"{command_description} failed for {repository_path}: {message}")


def get_current_commit(repository_path: Path | str) -> str:
	result = run_git_command(repository_path, ["rev-parse", "HEAD"])
	_raise_for_failed_git_command(repository_path, "git rev-parse HEAD", result)
	return result.stdout.strip()


def checkout_commit(repository_path: Path | str, commit: str) -> None:
	result = run_git_command(repository_path, ["checkout", commit])
	_raise_for_failed_git_command(repository_path, f"git checkout {commit}", result)
