from typing import Any, Union
from .frozen import FrozenDict
import json


class DictKeysDict(dict):
    """
    A dictionary where all keys are enforced to be FrozenDict instances. Any dictionary
    values are converted recursively to DictKeysDict, ensuring that all nested keys within
    these dictionary values are also FrozenDict instances.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.update(*args, **kwargs)

    def __getitem__(self, key: Union[str, FrozenDict]) -> Any:
        if isinstance(key, str):
            key = FrozenDict.from_string(key)
        return super().__getitem__(key)

    def __setitem__(self, key: Union[str, dict, FrozenDict], value: Any) -> None:
        key = self._ensure_frozendict(key)
        value = self._convert_value(value)
        super().__setitem__(key, value)

    def update(self, *args: Any, **kwargs: Any) -> None:
        for k, v in dict(*args, **kwargs).items():
            k = self._ensure_frozendict(k)
            v = self._convert_value(v)
            super().__setitem__(k, v)

    def setdefault(self, key: Union[str, dict, FrozenDict], default: Any = None) -> Any:
        key = self._ensure_frozendict(key)
        default = self._convert_value(default)
        return super().setdefault(key, default)

    def _ensure_frozendict(
        self, key: Union[str, dict]
    ) -> Union[FrozenDict, "DictKeysDict"]:
        """
        Ensures that the given key is a valid FrozenDict or a convertible string.

        Parameters:
            key (Union[str, dict]): The key to be ensured.

        Returns:
            Union[FrozenDict, DictKeysDict]: The ensured key.

        Raises:
            KeyError: If the key is not a valid FrozenDict or a convertible string.
        """
        if isinstance(key, str):
            return FrozenDict.from_string(key)
        elif isinstance(key, dict) and not isinstance(key, FrozenDict):
            return DictKeysDict(key)  # Convert nested dicts on keys to DictKeysDict
        elif not isinstance(key, FrozenDict):
            raise KeyError(
                f"Invalid key type: {type(key)}. Keys must be instances of FrozenDict or convertible strings."
            )
        return key

    def _convert_value(self, value: Any) -> Any:
        """
        Recursively convert dictionary values to DictKeysDict. If the value is a list or
        another iterable containing dictionaries, those dictionaries are also converted.
        """
        if isinstance(value, dict) and not isinstance(value, DictKeysDict):
            return DictKeysDict(
                {
                    self._ensure_frozendict(k): self._convert_value(v)
                    for k, v in value.items()
                }
            )
        elif isinstance(value, list):
            return [self._convert_value(item) for item in value]
        return value

    @classmethod
    def dumpJson(cls, obj: Any) -> str:
        """
        Serializes an object to a JSON string.

        Args:
            obj (Any): The object to be serialized.

        Returns:
            str: The serialized JSON string.

        This class method recursively converts the object to a JSON-serializable format. If the object is a `DictKeysDict`, it converts the keys to strings using `FrozenDict.toString()`. If the object is a list, it recursively converts each item in the list. If the object is a `FrozenDict`, it converts it to a string using `FrozenDict.toString()`. For any other object, it returns the object as is. The resulting object is then serialized using `json.dumps()`.

        Example:
            >>> class DictKeysDict(dict):
            ...     pass
            >>> class FrozenDict(dict):
            ...     @classmethod
            ...     def toString(cls, key):
            ...         return str(key)
            >>> obj = DictKeysDict({FrozenDict({'a': 1}): [FrozenDict({'b': 2}), {'c': 3}]})
            >>> DictKeysDict.dumpJson(obj)
            '{"{a: 1}": ["{b: 2}", {"c": 3}]}'
        """

        def parse(x: Any) -> Any:
            if isinstance(x, cls):
                return {FrozenDict.toString(k): parse(v) for k, v in x.items()}
            elif isinstance(x, list):
                return [parse(item) for item in x]
            elif isinstance(x, FrozenDict):
                return FrozenDict.toString(x)  # Special handling for simple FrozenDict
            else:
                return x

        return json.dumps(parse(obj))

    @classmethod
    def loadJson(cls, jsonStr: str) -> "DictKeysDict":
        """
        A method to load JSON from a string, recursively converting nested objects into DictKeysDict.
        Args:
            cls: The class method.
            jsonStr: The JSON string to be loaded.
        Returns:
            The loaded JSON object represented as a DictKeysDict.
        """

        def convert(obj: Any) -> Any:
            if isinstance(obj, dict):
                return DictKeysDict(
                    {FrozenDict.from_string(k): convert(v) for k, v in obj.items()}
                )
            elif isinstance(obj, list):
                return [convert(item) for item in obj]
            else:
                return obj

        return convert(json.loads(jsonStr))
