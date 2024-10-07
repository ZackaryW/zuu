#!untested

import os
import tomllib
import pickle
import toml
import typing

from zuu.std.hashlib import hash_file
from zuu.std.json import read_json


class QuickFileError(Exception):
    pass


def load_toml(path: str):
    with open(path, "rb") as f:
        return tomllib.load(f)


def save_toml(path: str, data: dict):
    with open(path, "w") as f:
        toml.dump(data, f)


def load_yaml(path: str):
    import yaml

    with open(path, "r") as f:
        return yaml.safe_load(f)


def save_yaml(path: str, data: dict):
    import yaml

    with open(path, "w") as f:
        yaml.dump(data, f)


def load_pickle(path: str):
    with open(path, "rb") as f:
        return pickle.load(f)


def save_pickle(path: str, data: dict):
    with open(path, "wb") as f:
        pickle.dump(data, f)


def _extension_read(path: str):
    _, ext = os.path.splitext(path)
    ext = ext.lstrip(".")
    loaders = {
        "json": read_json,
        "toml": load_toml,
        "yaml": load_yaml,
        "pickle": load_pickle,
    }
    loader = loaders.get(ext)
    if not loader:
        raise QuickFileError("Unsupported file type")
    return loader(path)


def _signature_load(path: str):
    with open(path, "rb") as f:
        fsignature = f.read(80)

    if fsignature.strip().startswith(b"{"):
        return read_json(path)
    elif b"=" in fsignature and b"[" not in fsignature[: fsignature.find(b"=")].strip():
        return load_toml(path)
    elif fsignature.strip().startswith(b"---"):
        return load_yaml(path)
    elif fsignature.startswith(pickle.dumps(pickle.MAGIC_NUMBER)):
        return load_pickle(path)
    else:
        raise QuickFileError("Unsupported file type or unknown signature")


def read_file(path: str, known_ext: str = None):
    if known_ext:
        return _extension_read(path)
    try:
        return _extension_read(path)
    except QuickFileError:
        return _signature_load(path)


class FilePropertyMeta:
    types = typing.Literal["mdate", "sha256", "size", "adate"]
    mapping: typing.Dict[types, typing.Callable[[str], typing.Any]] = {
        "mdate": os.path.getmtime,
        "sha256": lambda path: hash_file(path),
        "size": os.path.getsize,
        "adate": os.path.getatime,
    }
    callBackHooks: typing.Dict[str, typing.Callable] = {}

    @staticmethod
    def registerCallbackHook(
        *hooks: typing.Union[str, typing.Callable], callback: typing.Callable = None
    ):
        if callback is None and callable(hooks[-1]):
            callback = hooks[-1]
            hooks = hooks[:-1]

        for hook in hooks:
            FilePropertyMeta.callBackHooks[hook] = callback


class FileProperty:
    _properties = {}
    _cachedContent = {}

    def __init__(
        self,
        path: typing.Union[property, str],
        watching: typing.List[
            typing.Union[typing.List[FilePropertyMeta.types], FilePropertyMeta.types]
        ] = ["size", ["mdate", "sha256"]],
        customLoad: typing.Callable[[str], typing.Any] = None,
        customWatch: typing.Callable[[str], typing.Any] = None,
        fileCreate: typing.Callable[[str], typing.Any] = lambda path: open(
            path, "w"
        ).close(),
        callbacks: typing.List[typing.Union[str, typing.Callable]] = [],
    ):
        self.watching = watching
        self.path = path
        self.customLoad = customLoad
        self.customWatch = customWatch
        self.callbacks = callbacks

        path_str = self.path if isinstance(self.path, str) else None
        if fileCreate and path_str and not os.path.exists(path_str):
            fileCreate(path_str)

    def _needToRefetch(
        self,
        watch: typing.Union[
            typing.List[FilePropertyMeta.types], FilePropertyMeta.types
        ],
        record: typing.Dict,
    ):
        if isinstance(watch, list):
            return any(self._needToRefetch(w, record) for w in watch)

        old_value = record.get(watch)
        new_value = (
            self.customWatch(self.path)
            if watch == "custom"
            else FilePropertyMeta.mapping[watch](self.path)
        )
        if new_value != old_value:
            record[watch] = new_value
            return True
        return False

    def __get__(self, instance, owner):
        path = self.path(instance) if isinstance(self.path, property) else self.path

        if not os.path.exists(path):
            return None

        if path not in self._properties:
            self._properties[path] = {}

        if not self._needToRefetch(self.watching, self._properties[path]):
            return self._cachedContent.get(path)

        content = self.customLoad(path) if self.customLoad else read_file(path)
        self._cachedContent[path] = content

        for callback in self.callbacks:
            resolved_callback = FilePropertyMeta.callBackHooks.get(callback, callback)
            resolved_callback(path, content, self._properties[path])

        return content
