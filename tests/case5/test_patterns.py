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
    ("pattern", "matching", "not_matching"),
    [
        ("file?.py", "file1.py", "file10.py"),
        ("case[5-7]", "case6", "case8"),
        ("case[!0]", "case5", "case0"),
        ("docs/**/README.md", "docs/README.md", "docs/README.txt"),
    ],
)
def test_repository_glob_operators_have_bounded_semantics(
    pattern: str,
    matching: str,
    not_matching: str,
) -> None:
    glob = RepositoryGlob(pattern)

    assert glob.matches(matching)
    assert not glob.matches(not_matching)


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
        "src/a]/*.py",
        "src/[a[b]/*.py",
    ],
)
def test_repository_glob_rejects_unsafe_or_unbalanced_patterns(
    pattern: str,
) -> None:
    with pytest.raises(RepositoryPathError):
        RepositoryGlob(pattern)


def test_matching_rejects_an_unsafe_candidate_path() -> None:
    with pytest.raises(RepositoryPathError):
        RepositoryGlob("src/**").matches("../src/file.py")
