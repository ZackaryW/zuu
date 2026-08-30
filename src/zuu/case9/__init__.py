"""Temporary JSON-file configuration exposed through a process environment."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from types import TracebackType

__purpose__ = (
    "Hand structured settings to child processes like a temporary luggage locker, "
    "using an environment path as the claim ticket and cleaning up afterward."
)
__depends__ = ()


class TemporaryJsonEnvironmentError(ValueError):
    """Temporary JSON environment configuration or lifecycle handling failed."""


class TemporaryJsonEnvironment:
    """Provide a copied child environment that references a temporary JSON file.

    The payload is serialized when this context manager is constructed. The file
    is closed before the environment is yielded and removed whenever the context
    exits, including when the caller raises an exception.
    """

    __slots__ = (
        "_active",
        "_base",
        "_directory",
        "_has_payload",
        "_json",
        "_path",
        "_variable",
    )

    def __init__(
        self,
        payload: Mapping[str, object],
        *,
        variable: str,
        base: Mapping[str, str] | None = None,
        directory: str | os.PathLike[str] | None = None,
    ) -> None:
        _validate_variable(variable)
        if not isinstance(payload, Mapping):
            raise TemporaryJsonEnvironmentError("payload must be a mapping")
        if any(not isinstance(key, str) for key in payload):
            raise TemporaryJsonEnvironmentError("payload keys must be strings")
        if base is not None and not isinstance(base, Mapping):
            raise TemporaryJsonEnvironmentError("base environment must be a mapping")
        if base is not None:
            _validate_environment(base)

        snapshot = dict(payload)
        try:
            encoded = json.dumps(
                snapshot,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as error:
            raise TemporaryJsonEnvironmentError(
                f"payload is not JSON-serializable: {error}"
            ) from error

        self._variable = variable
        self._base = None if base is None else dict(base)
        self._directory = None if directory is None else Path(directory)
        self._json = encoded + "\n"
        self._has_payload = bool(snapshot)
        self._active = False
        self._path: Path | None = None

    def __enter__(self) -> dict[str, str]:
        if self._active:
            raise TemporaryJsonEnvironmentError("context manager is already active")

        environment = dict(os.environ if self._base is None else self._base)
        environment.pop(self._variable, None)
        self._active = True
        if not self._has_payload:
            return environment

        try:
            self._path = self._write_file()
        except Exception:
            self._active = False
            raise
        environment[self._variable] = str(self._path)
        return environment

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        path = self._path
        self._path = None
        self._active = False
        if path is None:
            return False

        try:
            path.unlink()
        except OSError as error:
            message = f"failed to remove temporary JSON file {path}: {error}"
            if exception is not None:
                exception.add_note(message)
                return False
            raise TemporaryJsonEnvironmentError(message) from error
        return False

    def _write_file(self) -> Path:
        try:
            descriptor, name = tempfile.mkstemp(
                prefix="zuu-json-",
                suffix=".json",
                dir=self._directory,
                text=True,
            )
        except OSError as error:
            raise TemporaryJsonEnvironmentError(
                f"could not create temporary JSON file: {error}"
            ) from error

        path = Path(name)
        try:
            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
                newline="\n",
            ) as stream:
                stream.write(self._json)
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            path.unlink(missing_ok=True)
            raise
        return path


def _validate_variable(variable: str) -> None:
    if (
        not isinstance(variable, str)
        or not variable
        or "=" in variable
        or "\0" in variable
    ):
        raise TemporaryJsonEnvironmentError("variable must be a valid environment name")


def _validate_environment(environment: Mapping[str, str]) -> None:
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in environment.items()):
        raise TemporaryJsonEnvironmentError("base environment keys and values must be strings")


__all__ = [
    "TemporaryJsonEnvironment",
    "TemporaryJsonEnvironmentError",
]
