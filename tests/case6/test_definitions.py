import pytest

from zuu.case5 import RepositoryGlob, RepositoryPathError
from zuu.case6 import AffectedTarget, AffectedTargets, AffectedTargetsError


def test_target_compiles_string_patterns_and_preserves_values() -> None:
    target = AffectedTarget("core", {"command": "pytest"}, ("src/core/**",))

    assert target.name == "core"
    assert target.value == {"command": "pytest"}
    assert target.patterns == (RepositoryGlob("src/core/**"),)


def test_target_accepts_precompiled_patterns() -> None:
    pattern = RepositoryGlob("docs/**")

    assert AffectedTarget("docs", "docs", (pattern,)).patterns == (pattern,)


def test_target_requires_a_name_and_patterns() -> None:
    with pytest.raises(AffectedTargetsError, match="name"):
        AffectedTarget("", "value", ("src/**",))
    with pytest.raises(AffectedTargetsError, match="at least one pattern"):
        AffectedTarget("core", "value", ())


def test_target_preserves_repository_glob_validation() -> None:
    with pytest.raises(RepositoryPathError):
        AffectedTarget("core", "value", ("../outside/**",))


def test_selector_requires_unique_nonempty_targets() -> None:
    target = AffectedTarget("core", "value", ("src/**",))

    with pytest.raises(AffectedTargetsError, match="at least one"):
        AffectedTargets(())
    with pytest.raises(AffectedTargetsError, match="duplicate"):
        AffectedTargets((target, target))


def test_definitions_accept_generators_without_losing_order() -> None:
    target = AffectedTarget(
        "core",
        "value",
        (pattern for pattern in ("src/**", "tests/**")),
    )
    selector = AffectedTargets(target for target in (target,))

    assert selector.targets == (target,)
    assert [pattern.pattern for pattern in target.patterns] == ["src/**", "tests/**"]
