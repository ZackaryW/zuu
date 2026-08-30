from pathlib import Path

import pytest

from zuu.case5 import ConfinedPath, StaleTargetError, TargetState


@pytest.mark.parametrize("setup", ["file", "directory", "absent"])
def test_unchanged_targets_revalidate_to_the_same_plan(
    tmp_path: Path,
    setup: str,
) -> None:
    root = tmp_path / "trusted"
    root.mkdir()
    target = root / "target"
    if setup == "file":
        target.write_text("value", encoding="utf-8")
    elif setup == "directory":
        target.mkdir()
    plan = ConfinedPath("target").inspect(root)

    assert plan.revalidate() is plan


def test_revalidation_detects_root_replacement(tmp_path: Path) -> None:
    root = tmp_path / "trusted"
    root.mkdir()
    plan = ConfinedPath("target").inspect(root)
    root.rename(tmp_path / "old-root")
    root.mkdir()

    with pytest.raises(StaleTargetError, match="stale"):
        plan.revalidate()


def test_revalidation_detects_ancestor_replacement(tmp_path: Path) -> None:
    root = tmp_path / "trusted"
    ancestor = root / "parent"
    ancestor.mkdir(parents=True)
    (ancestor / "target").write_text("old", encoding="utf-8")
    plan = ConfinedPath("parent/target").inspect(root)
    ancestor.rename(root / "old-parent")
    ancestor.mkdir()
    (ancestor / "target").write_text("new", encoding="utf-8")

    with pytest.raises(StaleTargetError, match="stale"):
        plan.revalidate()


@pytest.mark.parametrize("change", ["create", "remove", "replace", "kind"])
def test_revalidation_detects_target_state_or_evidence_changes(
    tmp_path: Path,
    change: str,
) -> None:
    root = tmp_path / "trusted"
    root.mkdir()
    target = root / "target"
    if change != "create":
        target.write_text("old", encoding="utf-8")
    plan = ConfinedPath("target").inspect(root)

    if change == "create":
        target.write_text("new", encoding="utf-8")
    elif change == "remove":
        target.unlink()
    else:
        target.rename(root / "old-target")
        if change == "replace":
            target.write_text("new", encoding="utf-8")
        else:
            target.mkdir()

    with pytest.raises(StaleTargetError, match="stale"):
        plan.revalidate()
    assert plan.state is (
        TargetState.ABSENT if change == "create" else TargetState.FILE
    )


def test_revalidation_detects_a_newly_occupied_absent_segment(tmp_path: Path) -> None:
    root = tmp_path / "trusted"
    root.mkdir()
    plan = ConfinedPath("future/nested/item.txt").inspect(root)
    (root / "future").mkdir()

    with pytest.raises(StaleTargetError, match="stale"):
        plan.revalidate()
    assert plan.missing == ("future", "nested", "item.txt")


def test_revalidation_detects_a_new_redirected_target(tmp_path: Path) -> None:
    root = tmp_path / "trusted"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("value", encoding="utf-8")
    plan = ConfinedPath("target").inspect(root)
    try:
        (root / "target").symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlinks are unavailable: {error}")

    with pytest.raises(StaleTargetError, match="redirected"):
        plan.revalidate()


def test_revalidation_detects_a_retargeted_declared_root(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    alias = tmp_path / "trusted"
    try:
        alias.symlink_to(first, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable: {error}")
    plan = ConfinedPath("target").inspect(alias)
    alias.unlink()
    alias.symlink_to(second, target_is_directory=True)

    with pytest.raises(StaleTargetError, match="stale"):
        plan.revalidate()


def test_directory_evidence_does_not_claim_descendant_content_integrity(
    tmp_path: Path,
) -> None:
    root = tmp_path / "trusted"
    directory = root / "output"
    directory.mkdir(parents=True)
    child = directory / "content.txt"
    child.write_text("before", encoding="utf-8")
    plan = ConfinedPath("output").inspect(root)

    child.write_text("after with different bytes", encoding="utf-8")

    assert plan.revalidate() is plan
    assert all(not hasattr(entry, "content") for entry in plan.evidence)
