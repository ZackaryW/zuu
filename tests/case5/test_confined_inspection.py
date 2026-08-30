import os
import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from zuu.case5 import ConfinedPath, ConfinedPathError, TargetState


@pytest.mark.parametrize(
    ("identity", "setup", "expected"),
    [
        ("data/item.txt", "file", TargetState.FILE),
        ("data/folder", "directory", TargetState.DIRECTORY),
        ("data/future/item.txt", "absent", TargetState.ABSENT),
    ],
)
def test_inspect_classifies_confined_targets_without_mutation(
    tmp_path: Path,
    identity: str,
    setup: str,
    expected: TargetState,
) -> None:
    root = tmp_path / "trusted"
    (root / "data").mkdir(parents=True)
    target = root.joinpath(*identity.split("/"))
    if setup == "file":
        target.write_text("value", encoding="utf-8")
    elif setup == "directory":
        target.mkdir()
    before = sorted(path.relative_to(root) for path in root.rglob("*"))

    plan = ConfinedPath(identity).inspect(root)

    assert plan.state is expected
    assert plan.declared_root == root.absolute()
    assert plan.root == root.resolve()
    assert plan.target == target
    assert plan.path.value == identity
    assert plan.allowed == frozenset(TargetState)
    assert sorted(path.relative_to(root) for path in root.rglob("*")) == before
    assert plan.missing == (
        ("future", "item.txt") if expected is TargetState.ABSENT else ()
    )


def test_evidence_is_ordered_and_frozen(tmp_path: Path) -> None:
    root = tmp_path / "trusted"
    target = root / "folder" / "item.txt"
    target.parent.mkdir(parents=True)
    target.write_text("value", encoding="utf-8")

    plan = ConfinedPath("folder/item.txt").inspect(root)

    assert [entry.relative_path for entry in plan.evidence] == [
        ".",
        "folder",
        "folder/item.txt",
    ]
    assert plan.evidence[-1].size == len("value")
    assert plan.evidence[0].size is None
    with pytest.raises(FrozenInstanceError):
        plan.state = TargetState.ABSENT  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        plan.evidence[-1].inode = 0  # type: ignore[misc]


def test_inspect_accepts_a_matching_explicit_allowed_state(tmp_path: Path) -> None:
    root = tmp_path / "trusted"
    root.mkdir()
    (root / "target").mkdir()

    plan = ConfinedPath("target").inspect(
        root,
        allowed={TargetState.DIRECTORY},
    )

    assert plan.state is TargetState.DIRECTORY
    assert plan.allowed == frozenset({TargetState.DIRECTORY})


def test_inspect_accepts_an_intentional_trusted_root_alias(tmp_path: Path) -> None:
    physical = tmp_path / "physical"
    physical.mkdir()
    alias = tmp_path / "trusted"
    try:
        alias.symlink_to(physical, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable: {error}")

    plan = ConfinedPath("target").inspect(alias)

    assert plan.declared_root == alias.absolute()
    assert plan.root == physical.resolve()
    assert plan.state is TargetState.ABSENT


@pytest.mark.parametrize(
    ("setup", "allowed", "observed"),
    [
        ("absent", {TargetState.FILE}, "absent"),
        ("file", {TargetState.ABSENT}, "file"),
        ("file", {TargetState.DIRECTORY}, "file"),
        ("directory", {TargetState.FILE}, "directory"),
    ],
)
def test_inspect_enforces_allowed_target_states(
    tmp_path: Path,
    setup: str,
    allowed: set[TargetState],
    observed: str,
) -> None:
    root = tmp_path / "trusted"
    root.mkdir()
    target = root / "target"
    if setup == "file":
        target.write_text("value", encoding="utf-8")
    elif setup == "directory":
        target.mkdir()

    with pytest.raises(ConfinedPathError, match=f"target state is {observed}"):
        ConfinedPath("target").inspect(root, allowed=allowed)


@pytest.mark.parametrize("allowed", [(), ["file"], 1])
def test_inspect_rejects_invalid_allowed_state_declarations(
    tmp_path: Path,
    allowed: object,
) -> None:
    tmp_path.joinpath("trusted").mkdir()

    with pytest.raises(ConfinedPathError, match="allowed target state"):
        ConfinedPath("target").inspect(
            tmp_path / "trusted",
            allowed=allowed,  # type: ignore[arg-type]
        )


def test_inspect_rejects_missing_or_non_directory_roots(tmp_path: Path) -> None:
    with pytest.raises(ConfinedPathError, match="root is unavailable"):
        ConfinedPath("target").inspect(tmp_path / "missing")

    root_file = tmp_path / "root.txt"
    root_file.write_text("value", encoding="utf-8")
    with pytest.raises(ConfinedPathError, match="root is not a directory"):
        ConfinedPath("target").inspect(root_file)


def test_inspect_rejects_a_non_directory_ancestor(tmp_path: Path) -> None:
    root = tmp_path / "trusted"
    root.mkdir()
    (root / "parent").write_text("value", encoding="utf-8")

    with pytest.raises(ConfinedPathError, match="ancestor is not a directory"):
        ConfinedPath("parent/target").inspect(root)


@pytest.mark.parametrize("link_at", ["target", "parent"])
def test_inspect_rejects_symbolic_link_descendants_even_within_root(
    tmp_path: Path,
    link_at: str,
) -> None:
    root = tmp_path / "trusted"
    real = root / "real"
    real.mkdir(parents=True)
    (real / "item.txt").write_text("value", encoding="utf-8")
    link = root / link_at
    try:
        link.symlink_to(
            real / "item.txt" if link_at == "target" else real,
            target_is_directory=link_at == "parent",
        )
    except OSError as error:
        pytest.skip(f"symlinks are unavailable: {error}")
    identity = "target" if link_at == "target" else "parent/item.txt"

    with pytest.raises(ConfinedPathError, match="redirected"):
        ConfinedPath(identity).inspect(root)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO creation is unavailable")
def test_inspect_rejects_an_unsupported_entry_kind(tmp_path: Path) -> None:
    root = tmp_path / "trusted"
    root.mkdir()
    os.mkfifo(root / "pipe")

    with pytest.raises(ConfinedPathError, match="unsupported kind"):
        ConfinedPath("pipe").inspect(root)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction behavior")
def test_inspect_rejects_a_windows_junction(tmp_path: Path) -> None:
    root = tmp_path / "trusted"
    target = root / "real"
    target.mkdir(parents=True)
    junction = root / "junction"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        pytest.skip(f"junction creation is unavailable: {result.stderr}")

    with pytest.raises(ConfinedPathError, match="redirected"):
        ConfinedPath("junction").inspect(root)
