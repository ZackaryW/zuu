from types import MappingProxyType, SimpleNamespace

import pytest

from zuu.case13 import AccessPolicy, deep_get, deep_has, deep_pop


@pytest.fixture(params=list(AccessPolicy))
def tree(request):
    policy = request.param
    if policy is AccessPolicy.ATTRIBUTE:
        branch = SimpleNamespace(value=None)
        root, path = SimpleNamespace(branch=branch), ["branch", "value"]
    elif policy is AccessPolicy.AUTO:
        branch = {"value": None}
        root, path = SimpleNamespace(branch=[branch]), ["branch", 0, "value"]
    else:
        branch = {"value": None}
        root, path = {"branch": branch}, ["branch", "value"]
    return root, path, policy


def test_has_and_pop_preserve_none_and_parent(tree) -> None:
    root, path, policy = tree
    parent = deep_get(root, path[:-1], policy=policy)
    assert deep_has(root, path, policy=policy)
    assert deep_pop(root, iter(path), policy=policy) is None
    assert not deep_has(root, path, policy=policy)
    assert deep_get(root, path[:-1], policy=policy) is parent
    assert not (vars(parent) if isinstance(parent, SimpleNamespace) else parent)


def test_missing_leaf_and_intermediates(tree) -> None:
    root, path, policy = tree
    fallback = object()
    for keys in (["absent", "leaf"], [*path[:-1], "absent"]):
        assert not deep_has(root, keys, policy=policy)
        assert deep_pop(root, keys, fallback, policy=policy) is fallback
        with pytest.raises((KeyError, AttributeError)):
            deep_pop(root, keys, policy=policy)
    assert deep_has(root, path, policy=policy)


@pytest.mark.parametrize("value", [False, 0, "", [], {}])
def test_has_and_pop_falsey_values(value) -> None:
    root = {"a": {"value": value}}
    assert deep_has(root, ["a", "value"])
    assert deep_pop(root, ["a", "value"]) is value
    assert root == {"a": {}}


def test_pop_deletes_list_index_and_shifts_remaining_elements() -> None:
    value = object()
    root = {"values": [0, value, 2]}
    assert deep_pop(root, ["values", -2]) is value
    assert root == {"values": [0, 2]}
    assert not deep_has(root, ["values", 20])
    assert deep_pop(root, ["values", 20], default="missing") == "missing"
    assert deep_pop(root, ["values", 20, "leaf"], default="missing") == "missing"
    with pytest.raises(IndexError):
        deep_pop(root, ["values", 20, "leaf"])


@pytest.mark.parametrize("policy", list(AccessPolicy))
def test_empty_paths(policy) -> None:
    assert deep_has(None, [], policy=policy)
    with pytest.raises(ValueError, match="at least one key"):
        deep_pop({}, [], default=None, policy=policy)


def test_read_only_container_deletion_is_not_absence() -> None:
    for root, key in ((MappingProxyType({"a": 1}), "a"), ((1,), 0)):
        assert deep_has(root, [key])
        with pytest.raises(TypeError):
            deep_pop(root, [key], default=None)


def test_attribute_property_deleter_and_slots() -> None:
    class Container:
        __slots__ = ("stored",)

        def __init__(self):
            self.stored = []

        @property
        def value(self):
            return self.stored

        @value.deleter
        def value(self):
            del self.stored

    root = Container()
    value = root.stored
    assert deep_pop(root, ["value"], policy="attribute") is value
    assert not deep_has(root, ["stored"], policy="attribute")


def test_deletion_errors_are_not_swallowed_by_default() -> None:
    class Item(dict):
        def __delitem__(self, key):
            raise KeyError("delete failed")

    class Attribute:
        value = 1

        def __delattr__(self, key):
            raise AttributeError("delete failed")

    for root, policy, error in (
        (Item(value=1), "item", KeyError),
        (Attribute(), "attribute", AttributeError),
    ):
        with pytest.raises(error, match="delete failed"):
            deep_pop(root, ["value"], default=None, policy=policy)
        assert deep_has(root, ["value"], policy=policy)


def test_queries_propagate_wrong_protocol_and_type_errors() -> None:
    class Broken(dict):
        def __getitem__(self, key):
            raise AttributeError("wrong protocol")

    for operation in (deep_has, deep_pop):
        with pytest.raises(AttributeError, match="wrong protocol"):
            operation(Broken(), ["value"], policy="auto")
        with pytest.raises(TypeError):
            operation({"value": None}, ["value", "child"])


def test_pop_resolves_each_getter_only_once() -> None:
    class Container:
        calls = 0
        child = {"value": 1}

        @property
        def branch(self):
            self.calls += 1
            return self.child

    root = Container()
    assert deep_pop(root, ["branch", "value"], policy="auto") == 1
    assert root.calls == 1
    assert root.child == {}
