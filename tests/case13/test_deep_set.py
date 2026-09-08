from collections import UserDict
from types import MappingProxyType

import pytest

from zuu.case13 import deep_get, deep_set


def test_create_nested_keys_and_replace_leaf_in_place() -> None:
    root = {}
    assert deep_set(root, ["a", "b", "c"], 1) is None
    assert root == {"a": {"b": {"c": 1}}}
    deep_set(root, ["a", "b", "c"], 2)
    deep_set(root, ["a", "sibling"], 3)
    assert root == {"a": {"b": {"c": 2}, "sibling": 3}}


def test_existing_containers_and_assigned_value_keep_identity() -> None:
    nested = {}
    root = {"a": nested}
    value = []
    deep_set(root, ["a", "value"], value)
    assert root["a"] is nested
    assert root["a"]["value"] is value
    value.append(3)
    assert deep_get(root, ["a", "value"]) == [3]


def test_mixed_containers_and_negative_list_indexes() -> None:
    root = {"users": [{"name": "first"}, {}]}
    deep_set(root, ["users", -1, "settings", "enabled"], True)
    deep_set(root, ["users", 0, "name"], "updated")
    assert root == {"users": [{"name": "updated"}, {"settings": {"enabled": True}}]}


def test_keys_and_generator_paths_are_literal() -> None:
    root = {}
    deep_set(root, iter(["a.b", (1, 2), 0]), "value")
    assert root == {"a.b": {(1, 2): {0: "value"}}}


def test_default_containers_are_independent_across_calls_and_levels() -> None:
    first, second = {}, {}
    deep_set(first, ["a", "b", "c"], 1)
    deep_set(first, ["sibling", "value"], 2)
    deep_set(second, ["a", "value"], 3)
    assert first["a"] is not first["a"]["b"]
    assert first["a"] is not first["sibling"]
    assert first["a"] is not second["a"]
    assert second == {"a": {"value": 3}}


def test_nullobject_is_deep_copied_for_every_missing_key() -> None:
    template = {"defaults": []}
    root = {}
    deep_set(root, ["a", "b", "value"], 1, nullobject=template)
    deep_set(root, ["other", "value"], 2, template)
    assert root == {
        "a": {"defaults": [], "b": {"defaults": [], "value": 1}},
        "other": {"defaults": [], "value": 2},
    }
    root["a"]["b"]["defaults"].append("only here")
    assert (
        root["a"]["defaults"] == root["other"]["defaults"] == template["defaults"] == []
    )


def test_custom_mapping_template_and_root() -> None:
    root = UserDict()
    template = UserDict({"default": True})
    deep_set(root, ["a", "b", "value"], 3, nullobject=template)
    assert isinstance(root["a"], UserDict)
    assert isinstance(root["a"]["b"], UserDict)
    assert deep_get(root, ["a", "b", "value"]) == 3
    assert template == {"default": True}


def test_list_template_can_supply_existing_indexes() -> None:
    template = [{}]
    root = {}
    deep_set(root, ["a", 0, "value"], 3, nullobject=template)
    assert root == {"a": [{"value": 3}]}
    assert template == [{}]


@pytest.mark.parametrize("value", [None, False, 0])
def test_existing_scalars_are_not_replaced(value) -> None:
    root = {"a": value}
    with pytest.raises(TypeError):
        deep_set(root, ["a", "b"], 1)
    assert root == {"a": value}


@pytest.mark.parametrize("keys", [["a", 2], ["a", -2, "value"]])
def test_lists_are_not_extended(keys) -> None:
    root = {"a": [{}]}
    with pytest.raises(IndexError):
        deep_set(root, keys, 1)
    assert root == {"a": [{}]}


def test_immutable_containers_can_be_traversed_but_not_assigned() -> None:
    child = {}
    root = MappingProxyType({"a": (child,)})
    deep_set(root, ["a", 0, "value"], 3)
    assert child == {"value": 3}
    with pytest.raises(TypeError):
        deep_set(root, ["new", "value"], 4)
    with pytest.raises(TypeError):
        deep_set(root, ["a", 0], 4)


@pytest.mark.parametrize("template", [None, [], 3, ()])
def test_unusable_template_does_not_attach_partial_branch(template) -> None:
    root = {"untouched": 1}
    with pytest.raises((TypeError, IndexError)):
        deep_set(root, ["missing", "leaf"], 2, nullobject=template)
    assert root == {"untouched": 1}


def test_deep_branch_failure_does_not_attach_partial_content() -> None:
    root = {}
    with pytest.raises(TypeError):
        deep_set(root, ["a", "b", []], 2)
    assert root == {}


def test_template_copy_failure_propagates_without_mutation() -> None:
    class Uncopyable:
        def __deepcopy__(self, memo):
            raise RuntimeError("cannot copy")

    root = {}
    with pytest.raises(RuntimeError, match="cannot copy"):
        deep_set(root, ["a", "value"], 1, nullobject=Uncopyable())
    assert root == {}
    deep_set(root, ["value"], 1, nullobject=Uncopyable())
    assert root == {"value": 1}


def test_empty_set_path_is_rejected() -> None:
    root = {"value": 1}
    with pytest.raises(ValueError, match="at least one key"):
        deep_set(root, [], 2)
    assert root == {"value": 1}


@pytest.mark.parametrize("keys", ["abc", b"abc", bytearray(b"abc"), None, 3])
def test_invalid_path_containers_do_not_modify_root(keys) -> None:
    root = {}
    with pytest.raises(TypeError):
        deep_set(root, keys, 1)
    assert root == {}


def test_path_is_consumed_before_mutation() -> None:
    def failing_keys():
        yield "a"
        raise RuntimeError("path failed")

    root = {}
    with pytest.raises(RuntimeError, match="path failed"):
        deep_set(root, failing_keys(), 1)
    assert root == {}


def test_deep_paths_do_not_require_recursive_traversal() -> None:
    root = {}
    keys = list(range(1500))
    deep_set(root, keys, "leaf")
    assert deep_get(root, keys) == "leaf"


def test_existing_template_children_and_siblings_are_preserved() -> None:
    template = {"nested": {"sibling": 1}}
    root = {}
    deep_set(root, ["a", "nested", "value"], 2, nullobject=template)
    assert root == {"a": {"nested": {"sibling": 1, "value": 2}}}
    assert template == {"nested": {"sibling": 1}}


def test_custom_item_protocol_and_assignment_errors() -> None:
    class Container:
        def __init__(self):
            self.values = {}

        def __getitem__(self, key):
            return self.values[key]

        def __setitem__(self, key, value):
            if key == "blocked":
                raise RuntimeError("assignment failed")
            self.values[key] = value

    root = Container()
    deep_set(root, ["a", "b"], 1)
    assert deep_get(root, ["a", "b"]) == 1
    with pytest.raises(RuntimeError, match="assignment failed"):
        deep_set(root, ["blocked", "leaf"], 2)
    assert root.values == {"a": {"b": 1}}
