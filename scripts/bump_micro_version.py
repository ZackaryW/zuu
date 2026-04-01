import argparse
import re
import subprocess
import sys
from pathlib import Path


PROJECT_VERSION_PATTERN = re.compile(r"^(?P<yearquarter>\d{6})\.(?P<minor>\d+)\.(?P<micro>\d+)$")
PYPROJECT_VERSION_LINE_PATTERN = re.compile(
    r'^(?P<prefix>version\s*=\s*")(?P<version>\d{6}\.\d+\.\d+)(?P<suffix>"\s*)$',
    re.MULTILINE,
)
VERSION_DIR_PATTERN = re.compile(r"^v(?P<yearquarter>\d{6})_(?P<minor>\d+)$")

STATUS_OK = "ok"
STATUS_BUMP_REQUIRED = "bump-required"
STATUS_BLOCKED = "blocked"


def parse_project_version(version: str) -> tuple[int, int, int] | None:
    match = PROJECT_VERSION_PATTERN.fullmatch(version)
    if match is None:
        return None

    return (
        int(match.group("yearquarter")),
        int(match.group("minor")),
        int(match.group("micro")),
    )


def parse_version_dir_name(name: str) -> tuple[int, int] | None:
    match = VERSION_DIR_PATTERN.fullmatch(name)
    if match is None:
        return None

    return int(match.group("yearquarter")), int(match.group("minor"))


def run_git_command(repository_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository_root), *args],
        capture_output=True,
        check=False,
        text=True,
    )


def _raise_for_failed_git_command(
    repository_root: Path,
    command_description: str,
    result: subprocess.CompletedProcess[str],
) -> None:
    if result.returncode == 0:
        return

    message = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
    raise RuntimeError(f"{command_description} failed for {repository_root}: {message}")


def get_staged_paths(repository_root: Path, diff_filter: str = "ACMR") -> list[str]:
    result = run_git_command(
        repository_root,
        ["diff", "--cached", "--name-only", f"--diff-filter={diff_filter}"],
    )
    _raise_for_failed_git_command(repository_root, "git diff --cached --name-only", result)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def read_file_from_revision(repository_root: Path, revision: str, relative_path: str) -> str:
    object_name = f":{relative_path}" if revision == "" else f"{revision}:{relative_path}"
    result = run_git_command(repository_root, ["show", object_name])
    _raise_for_failed_git_command(repository_root, f"git show {object_name}", result)
    return result.stdout


def version_dir_exists_in_revision(repository_root: Path, revision: str, version_dir_name: str) -> bool:
    version_dir_path = f"src/zuu/{version_dir_name}"
    result = run_git_command(
        repository_root,
        ["ls-tree", "-d", "--name-only", revision, "--", version_dir_path],
    )
    _raise_for_failed_git_command(repository_root, f"git ls-tree {revision} {version_dir_path}", result)
    return result.stdout.strip() != ""


def stage_path(repository_root: Path, relative_path: str) -> None:
    result = run_git_command(repository_root, ["add", "--", relative_path])
    _raise_for_failed_git_command(repository_root, f"git add {relative_path}", result)


def find_latest_version_dir(package_dir: Path) -> Path:
    version_dirs = [
        child
        for child in package_dir.iterdir()
        if child.is_dir() and parse_version_dir_name(child.name) is not None
    ]

    if not version_dirs:
        raise FileNotFoundError(f"No version directories found in {package_dir}")

    def version_key(child: Path) -> tuple[int, int]:
        parsed_version = parse_version_dir_name(child.name)
        if parsed_version is None:
            raise ValueError(f"Invalid version directory name: {child.name}")

        return parsed_version

    return max(version_dirs, key=version_key)


def read_project_version(pyproject_path: Path) -> str:
    contents = pyproject_path.read_text(encoding="utf-8")
    return read_project_version_from_text(contents, str(pyproject_path))


def write_project_version(pyproject_path: Path, new_version: str) -> None:
    contents = pyproject_path.read_text(encoding="utf-8")

    def replace_version(match: re.Match[str]) -> str:
        return f'{match.group("prefix")}{new_version}{match.group("suffix")}'

    updated_contents, replacements = PYPROJECT_VERSION_LINE_PATTERN.subn(replace_version, contents, count=1)
    if replacements != 1:
        raise ValueError(f"Could not update the project version in {pyproject_path}")

    pyproject_path.write_text(updated_contents, encoding="utf-8")


def read_project_version_from_text(contents: str, source_name: str) -> str:
    match = PYPROJECT_VERSION_LINE_PATTERN.search(contents)
    if match is None:
        raise ValueError(f"Could not find a simple project version in {source_name}")

    return match.group("version")


def bump_micro_version(pyproject_path: Path, package_dir: Path) -> tuple[str, str]:
    current_version = read_project_version(pyproject_path)
    parsed_project_version = parse_project_version(current_version)
    if parsed_project_version is None:
        raise ValueError(f"Unsupported project version format: {current_version}")

    latest_dir = find_latest_version_dir(package_dir)
    parsed_latest_dir = parse_version_dir_name(latest_dir.name)
    if parsed_latest_dir is None:
        raise ValueError(f"Unsupported version directory name: {latest_dir.name}")

    project_yearquarter, project_minor, project_micro = parsed_project_version
    latest_yearquarter, latest_minor = parsed_latest_dir
    if (project_yearquarter, project_minor) != (latest_yearquarter, latest_minor):
        raise ValueError(
            "Refusing to bump the micro version because the newest version directory does not match "
            f"pyproject.toml: latest directory is {latest_dir.name}, but project version is {current_version}. "
            "Create or adopt the new feature version instead."
        )

    next_version = f"{project_yearquarter}.{project_minor}.{project_micro + 1}"
    write_project_version(pyproject_path, next_version)
    return current_version, next_version


def evaluate_micro_version_for_staged_changes(
    pyproject_path: Path,
    package_dir: Path,
    repository_root: Path,
) -> tuple[str, str]:
    latest_dir = find_latest_version_dir(package_dir)
    current_version = read_project_version(pyproject_path)
    parsed_current_version = parse_project_version(current_version)
    parsed_latest_dir = parse_version_dir_name(latest_dir.name)
    if parsed_current_version is None or parsed_latest_dir is None:
        raise ValueError(
            f"Unsupported current version state: project={current_version!r}, latest_dir={latest_dir.name!r}"
        )

    current_yearquarter, current_minor, _ = parsed_current_version
    latest_yearquarter, latest_minor = parsed_latest_dir
    if (current_yearquarter, current_minor) != (latest_yearquarter, latest_minor):
        return (
            STATUS_BLOCKED,
            "The newest version directory does not match pyproject.toml. "
            f"Latest directory is {latest_dir.name}, but project version is {current_version}. "
            "Create or adopt the new feature version before committing.",
        )

    latest_prefix = f"src/zuu/{latest_dir.name}/"
    staged_paths = get_staged_paths(repository_root)
    staged_added_paths = get_staged_paths(repository_root, diff_filter="A")

    if not any(path == latest_prefix[:-1] or path.startswith(latest_prefix) for path in staged_paths):
        return STATUS_OK, "No staged changes under the newest version folder require a micro version bump."

    for path in staged_added_paths:
        path_parts = Path(path).parts
        if len(path_parts) < 3 or path_parts[:2] != ("src", "zuu"):
            continue

        version_dir_name = path_parts[2]
        if parse_version_dir_name(version_dir_name) is None:
            continue

        if not version_dir_exists_in_revision(repository_root, "HEAD", version_dir_name):
            return STATUS_OK, f"Detected a newly added version directory: {version_dir_name}."

    staged_version = read_project_version_from_text(
        read_file_from_revision(repository_root, "", "pyproject.toml"),
        "staged pyproject.toml",
    )
    head_version = read_project_version_from_text(
        read_file_from_revision(repository_root, "HEAD", "pyproject.toml"),
        "HEAD pyproject.toml",
    )
    parsed_staged_version = parse_project_version(staged_version)
    parsed_head_version = parse_project_version(head_version)
    if parsed_staged_version is None or parsed_head_version is None:
        raise ValueError(
            f"Unsupported project version format in pyproject.toml: staged={staged_version!r}, head={head_version!r}"
        )

    head_yearquarter, head_minor, head_micro = parsed_head_version
    staged_yearquarter, staged_minor, staged_micro = parsed_staged_version
    if (staged_yearquarter, staged_minor, staged_micro) == (head_yearquarter, head_minor, head_micro + 1):
        return STATUS_OK, f"Detected required micro version bump: {head_version} -> {staged_version}."

    return (
        STATUS_BUMP_REQUIRED,
        "Staged changes modify the newest version folder without adding a new version directory. "
        f"Bump pyproject.toml from {head_version} to {head_yearquarter}.{head_minor}.{head_micro + 1} "
        "by running: uv run python scripts/bump_micro_version.py",
    )


def check_micro_version_for_staged_changes(
    pyproject_path: Path,
    package_dir: Path,
    repository_root: Path,
) -> tuple[bool, str]:
    status, message = evaluate_micro_version_for_staged_changes(pyproject_path, package_dir, repository_root)
    return status == STATUS_OK, message


def ensure_micro_version_for_staged_changes(
    pyproject_path: Path,
    package_dir: Path,
    repository_root: Path,
) -> tuple[bool, str]:
    status, message = evaluate_micro_version_for_staged_changes(pyproject_path, package_dir, repository_root)
    if status == STATUS_OK:
        return False, message

    if status == STATUS_BLOCKED:
        raise ValueError(message)

    previous_version, next_version = bump_micro_version(pyproject_path, package_dir)
    stage_path(repository_root, pyproject_path.relative_to(repository_root).as_posix())
    return True, f"Automatically bumped pyproject.toml: {previous_version} -> {next_version}."


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Bump the no-breaking-change build segment in pyproject.toml when the newest versioned "
            "source folder still matches the current feature version."
        ),
    )
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "pyproject.toml",
        help="Path to pyproject.toml.",
    )
    parser.add_argument(
        "--package-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "src" / "zuu",
        help="Path to the zuu package directory that contains versioned folders.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Exit with a non-zero status when staged changes update the newest version folder without a "
            "corresponding micro version bump in pyproject.toml."
        ),
    )
    parser.add_argument(
        "--ensure-staged",
        action="store_true",
        help=(
            "Automatically bump and stage pyproject.toml when staged changes update the newest version "
            "folder without the required micro version increment."
        ),
    )
    args = parser.parse_args()

    try:
        if args.check and args.ensure_staged:
            raise ValueError("Choose either --check or --ensure-staged, not both.")

        if args.check:
            repository_root = args.pyproject.resolve().parent
            is_valid, message = check_micro_version_for_staged_changes(
                args.pyproject,
                args.package_dir,
                repository_root,
            )
            if not is_valid:
                print(message, file=sys.stderr)
                raise SystemExit(1)

            print(message)
            return

        if args.ensure_staged:
            repository_root = args.pyproject.resolve().parent
            changed, message = ensure_micro_version_for_staged_changes(
                args.pyproject,
                args.package_dir,
                repository_root,
            )
            print(message)
            if changed:
                return

            return

        previous_version, next_version = bump_micro_version(args.pyproject, args.package_dir)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"{previous_version} -> {next_version}")


if __name__ == "__main__":
    main()