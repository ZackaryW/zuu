from collections import defaultdict
from types import MappingProxyType

import pytest

import zuu.case13 as case13
from zuu.case13 import deep_get


def test_case13_metadata_and_exports() -> None:
    assert case13.__all__ == [
        "deep_get",
        "deep_set",
        "deep_has",
        "deep_pop",
        "deep_setdefault",
        "deep_update",
        "AccessPolicy",
    ]
    assert case13.__depends__ == ()
    assert "key paths" in case13.__purpose__


def test_read_mixed_mappings_lists_and_tuples() -> None:
    value = object()
    root = MappingProxyType({"users": [{"names": ("first", value)}]})
    assert deep_get(root, ["users", 0, "names", -1]) is value


def test_keys_are_literal_and_can_be_non_strings() -> None:
    root = {"a.b": {(1, 2): {3: "found"}}}
    assert deep_get(root, ("a.b", (1, 2), 3)) == "found"


def test_empty_path_returns_root_by_identity() -> None:
    root = {"a": 1}
    assert deep_get(root, [], default="unused") is root
    assert deep_get(None, []) is None


def test_generator_path_and_repeated_reads() -> None:
    root = {"a": {"b": 3}}
    for _ in range(2):
        assert deep_get(root, (key for key in ["a", "b"])) == 3
    assert root == {"a": {"b": 3}}


@pytest.mark.parametrize("value", [None, False, 0, "", [], {}])
def test_existing_falsey_values_are_not_missing(value: object) -> None:
    assert deep_get({"key": value}, ["key"], default="fallback") is value


@pytest.mark.parametrize(
    ("root", "keys", "error"),
    [
        ({}, ["absent"], KeyError),
        ({"a": {}}, ["a", "b"], KeyError),
        ({"a": []}, ["a", 0], IndexError),
    ],
)
def test_missing_keys_and_indexes(root, keys, error) -> None:
    with pytest.raises(error):
        deep_get(root, keys)
    fallback = object()
    assert deep_get(root, keys, default=fallback) is fallback
    assert deep_get(root, keys, None) is None


@pytest.mark.parametrize(
    ("root", "keys"),
    [({"a": None}, ["a", "b"]), ({"a": 3}, ["a", "b"]), ([1], ["0"]), ({}, [[]])],
)
def test_default_does_not_hide_type_errors(root, keys) -> None:
    with pytest.raises(TypeError):
        deep_get(root, keys, default=None)


@pytest.mark.parametrize("keys", ["abc", b"abc", bytearray(b"abc"), None, 3])
def test_invalid_path_containers(keys) -> None:
    with pytest.raises(TypeError):
        deep_get({}, keys, default=None)


def test_custom_item_access_and_errors() -> None:
    class Container:
        def __getitem__(self, key):
            if key == "value":
                return {"nested": 7}
            raise RuntimeError("lookup failed")

    assert deep_get(Container(), ["value", "nested"]) == 7
    with pytest.raises(RuntimeError, match="lookup failed"):
        deep_get(Container(), ["other"], default=None)


def test_attributes_are_not_looked_up() -> None:
    class Container:
        value = 3

    with pytest.raises(TypeError):
        deep_get(Container(), ["value"])


def test_container_default_behavior_is_preserved() -> None:
    root = defaultdict(dict)
    assert deep_get(root, ["created"]) == {}
    assert root == {"created": {}}
