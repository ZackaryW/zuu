import json
from pathlib import Path

import pytest

from zuu.case9 import TemporaryJsonEnvironment, TemporaryJsonEnvironmentError


def test_context_writes_deterministic_utf8_json_in_requested_directory(
    tmp_path: Path,
) -> None:
    payload = {"z": 2, "message": "héllo", "enabled": True}
    base = {"PATH": "example", "ZUU_CONFIG": "stale.json"}

    with TemporaryJsonEnvironment(
        payload,
        variable="ZUU_CONFIG",
        base=base,
        directory=tmp_path,
    ) as environment:
        path = Path(environment["ZUU_CONFIG"])
        assert path.parent == tmp_path
        assert path.read_text(encoding="utf-8") == (
            '{"enabled":true,"message":"héllo","z":2}\n'
        )
        assert json.loads(path.read_text(encoding="utf-8")) == payload
        assert environment["PATH"] == "example"

    assert not path.exists()
    assert base == {"PATH": "example", "ZUU_CONFIG": "stale.json"}
    assert payload == {"z": 2, "message": "héllo", "enabled": True}


def test_empty_payload_removes_stale_reference_without_creating_a_file(
    tmp_path: Path,
) -> None:
    before = set(tmp_path.iterdir())

    with TemporaryJsonEnvironment(
        {},
        variable="ZUU_CONFIG",
        base={"ZUU_CONFIG": "stale.json", "KEEP": "yes"},
        directory=tmp_path,
    ) as environment:
        assert environment == {"KEEP": "yes"}
        assert set(tmp_path.iterdir()) == before


def test_default_base_is_copied_when_the_context_is_entered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = TemporaryJsonEnvironment(
        {},
        variable="ZUU_CONFIG",
        directory=tmp_path,
    )
    monkeypatch.setenv("CASE9_LATE_VALUE", "visible")

    with context as environment:
        environment["CASE9_LATE_VALUE"] = "changed copy"
        assert environment["CASE9_LATE_VALUE"] == "changed copy"

    assert environment["CASE9_LATE_VALUE"] == "changed copy"
    assert __import__("os").environ["CASE9_LATE_VALUE"] == "visible"


def test_context_can_be_reused_sequentially(tmp_path: Path) -> None:
    context = TemporaryJsonEnvironment(
        {"value": 1},
        variable="ZUU_CONFIG",
        base={},
        directory=tmp_path,
    )

    with context as first_environment:
        first = Path(first_environment["ZUU_CONFIG"])
    with context as second_environment:
        second = Path(second_environment["ZUU_CONFIG"])
        assert second.exists()

    assert not first.exists()
    assert not second.exists()
    assert first != second


def test_active_context_rejects_reentry(tmp_path: Path) -> None:
    context = TemporaryJsonEnvironment(
        {"value": 1},
        variable="ZUU_CONFIG",
        base={},
        directory=tmp_path,
    )

    with context:
        with pytest.raises(TemporaryJsonEnvironmentError, match="already active"):
            context.__enter__()
