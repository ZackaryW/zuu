from collections import defaultdict
from types import MappingProxyType, SimpleNamespace

import pytest

from zuu.case13 import AccessPolicy, deep_get, deep_setdefault, deep_update


@pytest.fixture(params=list(AccessPolicy))
def tree(request):
    policy = request.param
    if policy is AccessPolicy.ATTRIBUTE:
        root, path = SimpleNamespace(branch=SimpleNamespace()), ["branch", "value"]
    elif policy is AccessPolicy.AUTO:
        root, path = SimpleNamespace(branch=[{}]), ["branch", 0, "value"]
    else:
        root, path = {"branch": {}}, ["branch", "value"]
    return root, path, policy


def test_setdefault_and_update_return_value_identity(tree) -> None:
    root, path, policy = tree
    value = []
    assert deep_setdefault(root, iter(path), value, policy=policy) is value
    assert deep_setdefault(root, path, "unused", policy=policy) is value
    calls = []
    result = [1]

    def transform(current):
        calls.append(current)
        return result

    assert deep_update(root, iter(path), transform, policy=policy) is result
    assert calls == [value]
    assert deep_get(root, path, policy=policy) is result


@pytest.mark.parametrize("value", [None, False, 0, "", [], {}])
def test_setdefault_preserves_falsey_values(tree, value) -> None:
    root, path, policy = tree
    assert deep_setdefault(root, path, value, policy=policy) is value
    assert deep_setdefault(root, path, "replacement", policy=policy) is value


def test_setdefault_defaults_to_none() -> None:
    root = {}
    assert deep_setdefault(root, ["a", "value"]) is None
    assert root == {"a": {"value": None}}


@pytest.mark.parametrize("policy", list(AccessPolicy))
def test_setdefault_builds_independent_missing_branches(policy) -> None:
    root = SimpleNamespace() if policy is AccessPolicy.ATTRIBUTE else {}
    first = deep_setdefault(root, ["a", "b", "value"], [], policy=policy)
    second = deep_setdefault(root, ["other", "value"], [], policy=policy)
    assert first is not second
    assert deep_get(root, ["a"], policy=policy) is not deep_get(
        root, ["a", "b"], policy=policy
    )


@pytest.mark.parametrize("policy", list(AccessPolicy))
def test_setdefault_copies_templates_and_respects_template_values(policy) -> None:
    attribute = policy is AccessPolicy.ATTRIBUTE
    template = SimpleNamespace(value=[]) if attribute else {"value": []}
    root = SimpleNamespace() if attribute else {}
    value = deep_setdefault(
        root, ["a", "b", "value"], "unused", template, policy=policy
    )
    assert value == []
    value.append(1)
    assert deep_get(root, ["a", "value"], policy=policy) == []
    assert deep_get(template, ["value"], policy=policy) == []


def test_setdefault_never_copies_unused_template() -> None:
    class Uncopyable:
        def __deepcopy__(self, memo):
            raise RuntimeError("copy failed")

    root = {"value": 1}
    assert deep_setdefault(root, ["value"], 2, Uncopyable()) == 1
    assert deep_setdefault(root, ["new"], 2, Uncopyable()) == 2
    with pytest.raises(RuntimeError, match="copy failed"):
        deep_setdefault(root, ["missing", "value"], 3, Uncopyable())
    assert root == {"value": 1, "new": 2}


@pytest.mark.parametrize("policy", list(AccessPolicy))
def test_setdefault_bad_leaf_does_not_attach_branch(policy) -> None:
    root = SimpleNamespace() if policy is AccessPolicy.ATTRIBUTE else {}
    with pytest.raises(TypeError):
        deep_setdefault(root, ["a", "b", []], 1, policy=policy)
    assert (vars(root) if isinstance(root, SimpleNamespace) else root) == {}


@pytest.mark.parametrize("keys", [["values", 3], ["values", 3, "leaf"]])
def test_setdefault_does_not_extend_lists(keys) -> None:
    root = {"values": [1]}
    with pytest.raises(IndexError):
        deep_setdefault(root, keys, 2)
    assert root == {"values": [1]}
    assert deep_setdefault(root, ["values", -1], 2) == 1


def test_setdefault_read_only_existing_leaf_is_allowed() -> None:
    root = MappingProxyType({"value": 1})
    assert deep_setdefault(root, ["value"], 2) == 1
    with pytest.raises(TypeError):
        deep_setdefault(root, ["missing", "leaf"], 2)
    assert dict(root) == {"value": 1}


def test_setdefault_respects_defaultdict_lookup() -> None:
    root = defaultdict(list)
    result = deep_setdefault(root, ["value"], "unused")
    assert result is root["value"]
    assert result == []


def test_update_missing_paths_never_call_transform(tree) -> None:
    root, path, policy = tree

    def unexpected(value):
        pytest.fail("transform was called on a missing path")

    for keys in (path, ["missing", "value"]):
        with pytest.raises((KeyError, AttributeError)):
            deep_update(root, keys, unexpected, policy=policy)


def test_update_callback_failures_leave_assignment_unchanged(tree) -> None:
    root, path, policy = tree
    deep_setdefault(root, path, 1, policy=policy)
    for error in (KeyError, IndexError, AttributeError, RuntimeError):

        def fail(value):
            raise error("transform failed")

        with pytest.raises(error, match="transform failed"):
            deep_update(root, path, fail, policy=policy)
        assert deep_get(root, path, policy=policy) == 1


def test_update_cannot_undo_callback_mutations() -> None:
    root = {"value": []}

    def mutate_then_fail(value):
        value.append(1)
        raise RuntimeError("failed after mutation")

    with pytest.raises(RuntimeError):
        deep_update(root, ["value"], mutate_then_fail)
    assert root == {"value": [1]}


def test_update_resolves_parent_and_invokes_transform_once() -> None:
    class Container:
        calls = 0
        child = {"value": 1}

        @property
        def branch(self):
            self.calls += 1
            return self.child

    root = Container()
    calls = []

    def transform(value):
        calls.append(value)
        return value + 1

    assert deep_update(root, ["branch", "value"], transform, policy="auto") == 2
    assert root.calls == 1
    assert calls == [1]
    assert root.child == {"value": 2}


def test_update_setter_failure_occurs_after_transform() -> None:
    calls = []
    root = MappingProxyType({"value": 1})

    def transform(value):
        calls.append(value)
        return 2

    with pytest.raises(TypeError):
        deep_update(root, ["value"], transform)
    assert calls == [1]
    assert root["value"] == 1


def test_update_keeps_resolved_parent_when_callback_replaces_ancestor() -> None:
    original = {"value": 1}
    replacement = {"value": 10}
    root = {"branch": original}

    def transform(value):
        root["branch"] = replacement
        return value + 1

    assert deep_update(root, ["branch", "value"], transform) == 2
    assert original == {"value": 2}
    assert root["branch"] is replacement
    assert replacement == {"value": 10}


def test_update_returns_transform_result_even_if_property_normalizes_it() -> None:
    class Container:
        stored = 1

        @property
        def value(self):
            return self.stored

        @value.setter
        def value(self, value):
            self.stored = value * 2

    root = Container()
    assert (
        deep_update(root, ["value"], lambda value: value + 1, policy="attribute") == 2
    )
    assert root.stored == 4
