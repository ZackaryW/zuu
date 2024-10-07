import json
from pathlib import Path
import typing


class OnChangeSaveDict(dict):
    def __init__(self, path, *args, __loose__=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.__loose = __loose__
        self.path = Path(path)
        if self.path.exists():
            with open(self.path, "r") as f:
                self.update(json.load(f))

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not self.__loose:
            raise ValueError("Nested dictionaries are not allowed")
        if (
            isinstance(value, typing.Iterable)
            and any(isinstance(v, dict) for v in value)
            and not self.__loose
        ):
            raise ValueError("Nested lists are not allowed")
        super().__setitem__(key, value)
        self._save()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._save()

    def update(self, *args, **kwargs):
        new_dict = dict(*args, **kwargs)
        for key, value in new_dict.items():
            if isinstance(value, dict) and not self.__loose:
                raise ValueError(
                    f"Nested dictionary found for key '{key}'. Nested dictionaries are not allowed"
                )
        super().update(new_dict)
        self._save()

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(dict(self), f, indent=2)


__all__ = ["OnChangeSaveDict"]
