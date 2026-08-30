import math
from pathlib import Path

import pytest

from zuu.case9 import TemporaryJsonEnvironment, TemporaryJsonEnvironmentError


def test_file_is_removed_when_caller_raises(tmp_path: Path) -> None:
    path: Path | None = None

    with pytest.raises(RuntimeError, match="caller failed"):
        with TemporaryJsonEnvironment(
            {"value": 1},
            variable="ZUU_CONFIG",
            base={},
            directory=tmp_path,
        ) as environment:
            path = Path(environment["ZUU_CONFIG"])
            raise RuntimeError("caller failed")

    assert path is not None
    assert not path.exists()


@pytest.mark.parametrize("variable", ["", "BAD=NAME", "BAD\0NAME", 1])
def test_invalid_environment_variable_is_rejected(variable: object) -> None:
    with pytest.raises(TemporaryJsonEnvironmentError, match="valid environment name"):
        TemporaryJsonEnvironment({}, variable=variable)  # type: ignore[arg-type]


@pytest.mark.parametrize("payload", [{"value": {1, 2}}, {"value": math.nan}])
def test_unserializable_or_nonfinite_payload_is_rejected(payload: object) -> None:
    with pytest.raises(TemporaryJsonEnvironmentError, match="not JSON-serializable"):
        TemporaryJsonEnvironment(payload, variable="ZUU_CONFIG")  # type: ignore[arg-type]


def test_non_mapping_payload_is_rejected() -> None:
    with pytest.raises(TemporaryJsonEnvironmentError, match="must be a mapping"):
        TemporaryJsonEnvironment([("value", 1)], variable="ZUU_CONFIG")  # type: ignore[arg-type]


def test_non_string_payload_keys_are_rejected() -> None:
    with pytest.raises(TemporaryJsonEnvironmentError, match="keys must be strings"):
        TemporaryJsonEnvironment({1: "value"}, variable="ZUU_CONFIG")  # type: ignore[dict-item]


def test_non_string_base_environment_is_rejected() -> None:
    with pytest.raises(TemporaryJsonEnvironmentError, match="keys and values"):
        TemporaryJsonEnvironment(
            {},
            variable="ZUU_CONFIG",
            base={"VALUE": 1},  # type: ignore[dict-item]
        )


def test_non_mapping_base_environment_is_rejected() -> None:
    with pytest.raises(TemporaryJsonEnvironmentError, match="must be a mapping"):
        TemporaryJsonEnvironment(
            {},
            variable="ZUU_CONFIG",
            base=[("VALUE", "one")],  # type: ignore[arg-type]
        )


def test_missing_temporary_directory_has_contextual_error(tmp_path: Path) -> None:
    context = TemporaryJsonEnvironment(
        {"value": 1},
        variable="ZUU_CONFIG",
        base={},
        directory=tmp_path / "missing",
    )

    with pytest.raises(TemporaryJsonEnvironmentError, match="could not create"):
        context.__enter__()


def test_cleanup_failure_is_raised_when_no_other_error_is_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_unlink = Path.unlink
    path: Path | None = None

    def fail_unlink(target: Path, *args: object, **kwargs: object) -> None:
        raise PermissionError("locked for test")

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    try:
        with pytest.raises(TemporaryJsonEnvironmentError, match="failed to remove"):
            with TemporaryJsonEnvironment(
                {"value": 1},
                variable="ZUU_CONFIG",
                base={},
                directory=tmp_path,
            ) as environment:
                path = Path(environment["ZUU_CONFIG"])
    finally:
        if path is not None:
            real_unlink(path, missing_ok=True)


def test_cleanup_failure_is_noted_on_an_active_caller_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_unlink = Path.unlink
    path: Path | None = None

    def fail_unlink(target: Path, *args: object, **kwargs: object) -> None:
        raise PermissionError("locked for test")

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    try:
        with pytest.raises(RuntimeError, match="caller failed") as captured:
            with TemporaryJsonEnvironment(
                {"value": 1},
                variable="ZUU_CONFIG",
                base={},
                directory=tmp_path,
            ) as environment:
                path = Path(environment["ZUU_CONFIG"])
                raise RuntimeError("caller failed")
        assert any("failed to remove" in note for note in captured.value.__notes__)
    finally:
        if path is not None:
            real_unlink(path, missing_ok=True)
