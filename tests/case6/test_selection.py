from zuu.case5 import RepositoryPath
from zuu.case6 import AffectedTarget, AffectedTargets


def selector() -> AffectedTargets[str]:
    return AffectedTargets(
        (
            AffectedTarget("core", "tests/core", ("src/core/**", "tests/core/**")),
            AffectedTarget("workflow", "tests/workflow", ("src/workflow/**",)),
            AffectedTarget("docs", "tests/docs", ("docs/**", "src/core/docs/**")),
        )
    )


def test_selection_unions_matches_in_declaration_order() -> None:
    selected = selector().select(
        ("src/workflow/state.py", "src/core/model.py", "src/core/docs/api.md")
    )

    assert tuple(target.name for target in selected) == ("core", "workflow", "docs")
    assert tuple(target.value for target in selected) == (
        "tests/core",
        "tests/workflow",
        "tests/docs",
    )


def test_selection_deduplicates_overlapping_patterns() -> None:
    selected = selector().select(("src/core/docs/api.md", "src/core/model.py"))

    assert tuple(target.name for target in selected) == ("core", "docs")


def test_selection_accepts_repository_path_objects() -> None:
    selected = selector().select((RepositoryPath("docs/guide.md"),))

    assert tuple(target.name for target in selected) == ("docs",)


def test_selection_returns_empty_for_no_changed_paths() -> None:
    assert selector().select(()) == ()


def test_unknown_path_conservatively_selects_every_target() -> None:
    assert selector().select(("README.md",)) == selector().targets


def test_invalid_path_conservatively_selects_every_target() -> None:
    assert selector().select(("../outside.py",)) == selector().targets
