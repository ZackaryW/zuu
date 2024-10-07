import json
import copy


class FrozenDict(dict):
    """
    A dictionary that cannot be modified after it is created.

    This class is similar to the built-in `frozenset` data structure, but
    for dictionaries instead of sets.
    """

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and not kwargs and isinstance(args[0], str):
            base = {"string": args[0]}
        else:
            base = sorted(dict(*args, **kwargs).items())

        super().__init__(tuple(base))

    def __hash__(self):
        return hash(tuple(sorted(self.items())))

    def __copy__(self):
        return FrozenDict(self)

    def __deepcopy__(self, memo):
        return FrozenDict(copy.deepcopy(dict(self), memo))

    def __setitem__(self, key, value):
        raise NotImplementedError

    def __delitem__(self, key):
        raise NotImplementedError

    def __setattr__(self, key, value):
        raise AttributeError

    def __delattr__(self, key):
        raise AttributeError

    def __str__(self):
        return str(sorted(dict(self)))

    def __repr__(self):
        return repr(dict(self))

    @classmethod
    def from_string(cls, string):
        if "{" not in string:
            return cls({"string": string})
        try:
            resolved = json.loads(string)
        except json.decoder.JSONDecodeError as e:
            print(f"JSON decoding error: {e}")
            resolved = {"string": string}
        return cls(resolved)

    def to_json(self):
        return json.dumps(dict(self))

    def fromJSON(json_str):
        return FrozenDict(json.loads(json_str))

    @classmethod
    def toString(cls, key):
        if isinstance(key, FrozenDict) and len(key) == 1 and "string" in key:
            # if the key is string
            return key["string"]
        else:
            return json.dumps(dict(key))


__all__ = ["FrozenDict"]
