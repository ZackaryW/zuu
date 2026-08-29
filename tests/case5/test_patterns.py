import pytest

from zuu.case5 import RepositoryGlob, RepositoryPath, RepositoryPathError


@pytest.mark.parametrize(
    ("path", "pattern", "expected"),
    [
        ("src/zuu/core.py", "src/**/*.py", True),
        ("src/core.py", "src/**/*.py", True),
        ("features/core/main.feature", "features/*/*.feature", True),
        ("features/core/nested/main.feature", "features/*/*.feature", False),
        ("docs/case7/README.md", "docs/case?/README.md", True),
        ("src/case5", "src/case[!0]", True),
    ],
)
def test_repository_glob_matches_the_complete_path(
    path: str,
    pattern: str,
    expected: bool,
) -> None:
    assert RepositoryGlob(pattern).matches(path) is expected


def test_repository_glob_accepts_a_repository_path() -> None:
    assert RepositoryGlob("src/**").matches(RepositoryPath("src/zuu/case5"))


@pytest.mark.parametrize(
    "pattern",
    [
        "",
        "/**/*.py",
        "../**",
        "src\\**\\*.py",
        "src//*.py",
        "src/**.py",
        "src/a**b",
        "src/[abc/*.py",
        "src/[]/*.py",
        "src/[!]/*.py",
    ],
)
def test_repository_glob_rejects_unsafe_or_unbalanced_patterns(
    pattern: str,
) -> None:
    with pytest.raises(RepositoryPathError):
        RepositoryGlob(pattern)
