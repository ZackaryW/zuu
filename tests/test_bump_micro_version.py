import importlib.util
import sys
from pathlib import Path

import pytest


def _load_bump_micro_version_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "bump_micro_version.py"
    spec = importlib.util.spec_from_file_location("bump_micro_version_script", script_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("bump_micro_version_script", module)
    spec.loader.exec_module(module)
    return module


bump_micro_version_script = _load_bump_micro_version_module()
bump_micro_version = bump_micro_version_script.bump_micro_version
check_micro_version_for_staged_changes = bump_micro_version_script.check_micro_version_for_staged_changes
ensure_micro_version_for_staged_changes = bump_micro_version_script.ensure_micro_version_for_staged_changes
parse_project_version = bump_micro_version_script.parse_project_version


def test_parse_project_version() -> None:
    assert parse_project_version("202602.1.0") == (202602, 1, 0)
    assert parse_project_version("202602.1") is None
    assert parse_project_version("v202602_1") is None


def test_bump_micro_version_updates_pyproject_when_latest_dir_matches(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        "[project]\nname = \"zuu\"\nversion = \"202602.1.3\"\n",
        encoding="utf-8",
    )
    package_dir = tmp_path / "src" / "zuu"
    (package_dir / "v202602_1").mkdir(parents=True)
    (package_dir / "current").mkdir()

    previous_version, next_version = bump_micro_version(pyproject_path, package_dir)

    assert previous_version == "202602.1.3"
    assert next_version == "202602.1.4"
    assert pyproject_path.read_text(encoding="utf-8") == (
        "[project]\nname = \"zuu\"\nversion = \"202602.1.4\"\n"
    )


def test_bump_micro_version_refuses_when_latest_dir_has_new_feature_version(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    original_contents = "[project]\nname = \"zuu\"\nversion = \"202602.1.3\"\n"
    pyproject_path.write_text(original_contents, encoding="utf-8")
    package_dir = tmp_path / "src" / "zuu"
    (package_dir / "v202602_1").mkdir(parents=True)
    (package_dir / "v202603_1").mkdir()

    with pytest.raises(ValueError, match="Refusing to bump the micro version"):
        bump_micro_version(pyproject_path, package_dir)

    assert pyproject_path.read_text(encoding="utf-8") == original_contents


def test_check_micro_version_for_staged_changes_requires_bump(monkeypatch, tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text("[project]\nversion = \"202602.1.1\"\n", encoding="utf-8")
    package_dir = tmp_path / "src" / "zuu"
    (package_dir / "v202602_1").mkdir(parents=True)

    monkeypatch.setattr(
        bump_micro_version_script,
        "get_staged_paths",
        lambda repository_root, diff_filter="ACMR": ["src/zuu/v202602_1/gh.py"] if diff_filter == "ACMR" else [],
    )
    monkeypatch.setattr(
        bump_micro_version_script,
        "read_file_from_revision",
        lambda repository_root, revision, relative_path: (
            "[project]\nversion = \"202602.1.1\"\n"
            if revision == ""
            else "[project]\nversion = \"202602.1.0\"\n"
        ),
    )

    is_valid, message = check_micro_version_for_staged_changes(pyproject_path, package_dir, tmp_path)

    assert is_valid is True
    assert message == "Detected required micro version bump: 202602.1.0 -> 202602.1.1."


def test_check_micro_version_for_staged_changes_fails_without_bump(monkeypatch, tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text("[project]\nversion = \"202602.1.0\"\n", encoding="utf-8")
    package_dir = tmp_path / "src" / "zuu"
    (package_dir / "v202602_1").mkdir(parents=True)

    monkeypatch.setattr(
        bump_micro_version_script,
        "get_staged_paths",
        lambda repository_root, diff_filter="ACMR": ["src/zuu/v202602_1/gh.py"] if diff_filter == "ACMR" else [],
    )
    monkeypatch.setattr(
        bump_micro_version_script,
        "read_file_from_revision",
        lambda repository_root, revision, relative_path: "[project]\nversion = \"202602.1.0\"\n",
    )

    is_valid, message = check_micro_version_for_staged_changes(pyproject_path, package_dir, tmp_path)

    assert is_valid is False
    assert "by running: uv run python scripts/bump_micro_version.py" in message


def test_check_micro_version_for_staged_changes_skips_when_new_version_dir_is_added(monkeypatch, tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text("[project]\nversion = \"202603.1.0\"\n", encoding="utf-8")
    package_dir = tmp_path / "src" / "zuu"
    (package_dir / "v202603_1").mkdir(parents=True)

    monkeypatch.setattr(
        bump_micro_version_script,
        "get_staged_paths",
        lambda repository_root, diff_filter="ACMR": ["src/zuu/v202603_1/gh.py"],
    )
    monkeypatch.setattr(
        bump_micro_version_script,
        "version_dir_exists_in_revision",
        lambda repository_root, revision, version_dir_name: False,
    )

    is_valid, message = check_micro_version_for_staged_changes(pyproject_path, package_dir, tmp_path)

    assert is_valid is True
    assert message == "Detected a newly added version directory: v202603_1."


def test_check_micro_version_for_staged_changes_fails_when_latest_dir_and_project_version_diverge(
    monkeypatch,
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text("[project]\nversion = \"202602.1.0\"\n", encoding="utf-8")
    package_dir = tmp_path / "src" / "zuu"
    (package_dir / "v202603_1").mkdir(parents=True)

    monkeypatch.setattr(bump_micro_version_script, "get_staged_paths", lambda repository_root, diff_filter="ACMR": [])

    is_valid, message = check_micro_version_for_staged_changes(pyproject_path, package_dir, tmp_path)

    assert is_valid is False
    assert "Create or adopt the new feature version before committing." in message


def test_ensure_micro_version_for_staged_changes_bumps_and_stages(monkeypatch, tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text("[project]\nversion = \"202602.1.0\"\n", encoding="utf-8")
    package_dir = tmp_path / "src" / "zuu"
    (package_dir / "v202602_1").mkdir(parents=True)
    staged_paths: list[str] = []

    monkeypatch.setattr(
        bump_micro_version_script,
        "evaluate_micro_version_for_staged_changes",
        lambda pyproject_path, package_dir, repository_root: (
            bump_micro_version_script.STATUS_BUMP_REQUIRED,
            "needs bump",
        ),
    )
    monkeypatch.setattr(
        bump_micro_version_script,
        "stage_path",
        lambda repository_root, relative_path: staged_paths.append(relative_path),
    )

    changed, message = ensure_micro_version_for_staged_changes(pyproject_path, package_dir, tmp_path)

    assert changed is True
    assert message == "Automatically bumped pyproject.toml: 202602.1.0 -> 202602.1.1."
    assert staged_paths == ["pyproject.toml"]
    assert pyproject_path.read_text(encoding="utf-8") == "[project]\nversion = \"202602.1.1\"\n"


def test_ensure_micro_version_for_staged_changes_noops_when_already_valid(monkeypatch, tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text("[project]\nversion = \"202602.1.1\"\n", encoding="utf-8")
    package_dir = tmp_path / "src" / "zuu"
    (package_dir / "v202602_1").mkdir(parents=True)

    monkeypatch.setattr(
        bump_micro_version_script,
        "evaluate_micro_version_for_staged_changes",
        lambda pyproject_path, package_dir, repository_root: (
            bump_micro_version_script.STATUS_OK,
            "Detected required micro version bump: 202602.1.0 -> 202602.1.1.",
        ),
    )

    changed, message = ensure_micro_version_for_staged_changes(pyproject_path, package_dir, tmp_path)

    assert changed is False
    assert message == "Detected required micro version bump: 202602.1.0 -> 202602.1.1."


def test_ensure_micro_version_for_staged_changes_raises_when_blocked(monkeypatch, tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text("[project]\nversion = \"202602.1.0\"\n", encoding="utf-8")
    package_dir = tmp_path / "src" / "zuu"
    (package_dir / "v202603_1").mkdir(parents=True)

    monkeypatch.setattr(
        bump_micro_version_script,
        "evaluate_micro_version_for_staged_changes",
        lambda pyproject_path, package_dir, repository_root: (
            bump_micro_version_script.STATUS_BLOCKED,
            "Create or adopt the new feature version before committing.",
        ),
    )

    with pytest.raises(ValueError, match="Create or adopt the new feature version before committing."):
        ensure_micro_version_for_staged_changes(pyproject_path, package_dir, tmp_path)