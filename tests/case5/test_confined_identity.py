from dataclasses import FrozenInstanceError

import pytest

from zuu.case5 import (
    ConfinedPath,
    ConfinedPathError,
    ConfinedTargetPlan,
    RepositoryGlob,
    RepositoryPath,
    StaleTargetError,
    TargetEvidence,
    TargetState,
)


def test_confined_path_preserves_one_canonical_portable_identity() -> None:
    path = ConfinedPath("profiles/team/default.toml")

    assert path.value == "profiles/team/default.toml"
    assert path.parts == ("profiles", "team", "default.toml")
    assert str(path) == "profiles/team/default.toml"


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "../escape",
        "a/../escape",
        "/absolute",
        "C:/drive",
        "a\\b",
        "a//b",
        "a/./b",
        "bad\x00path",
    ],
)
def test_confined_path_rejects_unsafe_or_noncanonical_values(value: str) -> None:
    with pytest.raises(ConfinedPathError, match="confined path"):
        ConfinedPath(value)


def test_confined_path_requires_a_string() -> None:
    with pytest.raises(ConfinedPathError, match="must be a string"):
        ConfinedPath(42)  # type: ignore[arg-type]


def test_confined_path_is_frozen() -> None:
    path = ConfinedPath("target")

    with pytest.raises(FrozenInstanceError):
        path.value = "changed"  # type: ignore[misc]


def test_new_exports_do_not_replace_existing_case5_imports() -> None:
    assert ConfinedTargetPlan is not None
    assert TargetEvidence is not None
    assert TargetState.FILE.value == "file"
    assert issubclass(StaleTargetError, ConfinedPathError)
    assert RepositoryPath("src/file.py").value == "src/file.py"
    assert RepositoryGlob("src/**").matches("src/file.py")
