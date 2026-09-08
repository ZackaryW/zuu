from collections import UserDict, UserList
from dataclasses import dataclass
from types import MappingProxyType, SimpleNamespace

import pytest

from zuu.case13 import AccessPolicy, deep_get, deep_set


@pytest.mark.parametrize(
    "policy", [AccessPolicy.ATTRIBUTE, "attribute", AccessPolicy.AUTO, "auto"]
)
def test_attribute_reads_and_writes(policy) -> None:
    @dataclass
    class Person:
        address: SimpleNamespace

    person = Person(SimpleNamespace(city="Paris"))
    assert deep_get(person, ["address", "city"], policy=policy) == "Paris"
    value = []
    assert deep_set(person, ["address", "city"], value, policy=policy) is None
    assert person.address.city is value


@pytest.mark.parametrize("policy", list(AccessPolicy))
def test_empty_paths_preserve_the_contract(policy) -> None:
    root = object()
    assert deep_get(root, [], policy=policy) is root
    with pytest.raises(ValueError, match="at least one key"):
        deep_set(root, [], 1, policy=policy)


@pytest.mark.parametrize("policy", [AccessPolicy.ITEM, "item"])
def test_explicit_item_policy(policy) -> None:
    root = {"a": [1]}
    deep_set(root, ["a", 0], 2, policy=policy)
    assert deep_get(root, ["a", 0], policy=policy) == 2


def test_auto_changes_modes_at_each_step() -> None:
    person = SimpleNamespace(address=SimpleNamespace(city="Paris"))
    root = SimpleNamespace(data=MappingProxyType({"people": (person,)}))
    keys = ["data", "people", -1, "address", "city"]
    assert deep_get(root, keys, policy=AccessPolicy.AUTO) == "Paris"
    deep_set(root, keys, "London", policy=AccessPolicy.AUTO)
    assert person.address.city == "London"


def test_auto_recognizes_mapping_and_sequence_implementations() -> None:
    root = UserDict(people=UserList([SimpleNamespace(name="Ada")]))
    deep_set(root, ["people", 0, "name"], "Grace", policy=AccessPolicy.AUTO)
    assert deep_get(root, ["people", 0, "name"], policy="auto") == "Grace"
    assert deep_get("abc", [1], policy="auto") == "b"


def test_policy_is_explicit_when_both_access_styles_exist() -> None:
    class Both(dict):
        name = "attribute"

    root = Both(name="item")
    assert deep_get(root, ["name"]) == "item"
    assert deep_get(root, ["name"], policy="auto") == "item"
    assert deep_get(root, ["name"], policy="attribute") == "attribute"
    deep_set(root, ["name"], "new attribute", policy="attribute")
    assert root["name"] == "item"
    deep_set(root, ["name"], "new item", policy="auto")
    assert root.name == "new attribute"
    assert root["name"] == "new item"


def test_auto_does_not_fall_back_between_access_styles() -> None:
    class Both(dict):
        name = "attribute"

    root = Both()
    with pytest.raises(KeyError):
        deep_get(root, ["name"], policy="auto")
    assert deep_get(root, ["name"], default=None, policy="auto") is None
    deep_set(root, ["name", "child"], 1, policy="auto")
    assert root == {"name": {"child": 1}}
    assert root.name == "attribute"


def test_unregistered_custom_item_objects_use_attributes_in_auto() -> None:
    class Container:
        name = "attribute"

        def __getitem__(self, key):
            return "item"

    root = Container()
    assert deep_get(root, ["name"], policy="auto") == "attribute"
    assert deep_get(root, ["name"], policy="item") == "item"
    with pytest.raises(AttributeError):
        deep_get(root, ["missing"], policy="auto")


@pytest.mark.parametrize("policy", [AccessPolicy.ATTRIBUTE, AccessPolicy.AUTO])
def test_missing_attributes_raise_or_return_default(policy) -> None:
    root = SimpleNamespace(child=SimpleNamespace())
    with pytest.raises(AttributeError):
        deep_get(root, ["child", "missing"], policy=policy)
    fallback = object()
    assert (
        deep_get(root, ["child", "missing"], default=fallback, policy=policy)
        is fallback
    )
    for value in (None, False, 0, "", []):
        root.value = value
        assert deep_get(root, ["value"], default=fallback, policy=policy) is value


@pytest.mark.parametrize("policy", [AccessPolicy.ATTRIBUTE, AccessPolicy.AUTO])
def test_missing_attributes_create_independent_namespaces(policy) -> None:
    first, second = SimpleNamespace(), SimpleNamespace()
    deep_set(first, ["a", "b", "value"], 1, policy=policy)
    deep_set(first, ["sibling", "value"], 2, policy=policy)
    deep_set(second, ["a", "value"], 3, policy=policy)
    assert first.a.b.value == 1
    assert first.a is not first.a.b
    assert first.a is not first.sibling
    assert first.a is not second.a


def test_auto_missing_nodes_follow_parent_access_mode() -> None:
    root = SimpleNamespace(data={})
    deep_set(root, ["data", "a", "b"], 1, policy="auto")
    deep_set(root, ["attributes", "a", "b"], 2, policy="auto")
    assert root.data == {"a": {"b": 1}}
    assert root.attributes.a.b == 2


@pytest.mark.parametrize("policy", [AccessPolicy.ATTRIBUTE, AccessPolicy.AUTO])
def test_attribute_template_is_copied_at_each_missing_component(policy) -> None:
    template = SimpleNamespace(labels=[])
    root = SimpleNamespace()
    deep_set(root, ["a", "b", "value"], 1, nullobject=template, policy=policy)
    root.a.b.labels.append("one")
    assert root.a.labels == template.labels == []
    assert root.a.b.value == 1


def test_auto_honors_an_explicit_mapping_template_for_missing_attributes() -> None:
    root = SimpleNamespace()
    template = {"labels": []}
    deep_set(root, ["a", "b", "value"], 1, nullobject=template, policy="auto")
    assert root.a == {"labels": [], "b": {"labels": [], "value": 1}}
    root.a["b"]["labels"].append(2)
    assert root.a["labels"] == template["labels"] == []


@pytest.mark.parametrize("key", [1, None, ("a",)])
def test_attribute_keys_must_be_strings(key) -> None:
    root = SimpleNamespace()
    with pytest.raises(TypeError):
        deep_get(root, [key], default=None, policy="attribute")
    with pytest.raises(TypeError):
        deep_set(root, ["new", key], 1, policy="attribute")
    assert vars(root) == {}


def test_attribute_names_are_literal() -> None:
    root = SimpleNamespace()
    deep_set(root, ["a.b"], 3, policy="attribute")
    assert deep_get(root, ["a.b"], policy="attribute") == 3
    assert not hasattr(root, "a")


@pytest.mark.parametrize("policy", [AccessPolicy.ATTRIBUTE, AccessPolicy.AUTO])
def test_existing_none_is_not_replaced(policy) -> None:
    root = SimpleNamespace(child=None)
    with pytest.raises(AttributeError):
        deep_set(root, ["child", "new", "value"], 1, policy=policy)
    assert root.child is None


@pytest.mark.parametrize("policy", [AccessPolicy.ATTRIBUTE, AccessPolicy.AUTO])
def test_read_only_properties_and_slots(policy) -> None:
    class Person:
        __slots__ = ("name",)

        def __init__(self):
            self.name = "Ada"

        @property
        def address(self):
            return "read only"

    root = Person()
    deep_set(root, ["name"], "Grace", policy=policy)
    assert deep_get(root, ["name"], policy=policy) == "Grace"
    with pytest.raises(AttributeError):
        deep_set(root, ["address"], "new", policy=policy)
    with pytest.raises(AttributeError):
        deep_set(root, ["new", "leaf"], 1, policy=policy)
    assert root.address == "read only"


def test_properties_and_dynamic_attributes_use_python_semantics() -> None:
    class Container:
        def __init__(self):
            self._value = 1

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, value):
            self._value = value * 2

        def __getattr__(self, key):
            if key == "dynamic":
                return SimpleNamespace(value=7)
            raise AttributeError(key)

    root = Container()
    deep_set(root, ["value"], 3, policy="attribute")
    assert deep_get(root, ["value"], policy="attribute") == 6
    assert deep_get(root, ["dynamic", "value"], policy="auto") == 7


@pytest.mark.parametrize("error", [KeyError, IndexError, RuntimeError])
def test_attribute_errors_from_other_protocols_are_not_missing(error) -> None:
    class Broken:
        @property
        def child(self):
            raise error("broken property")

    root = Broken()
    with pytest.raises(error):
        deep_get(root, ["child"], default=None, policy="attribute")
    with pytest.raises(error):
        deep_set(root, ["child", "value"], 1, policy="attribute")


def test_item_attribute_errors_are_not_missing() -> None:
    class Broken(dict):
        def __getitem__(self, key):
            raise AttributeError("broken item access")

    for policy in (AccessPolicy.ITEM, AccessPolicy.AUTO):
        with pytest.raises(AttributeError):
            deep_get(Broken(), ["child"], default=None, policy=policy)
        with pytest.raises(AttributeError):
            deep_set(Broken(), ["child", "value"], 1, policy=policy)


def test_property_attribute_error_has_normal_missing_attribute_semantics() -> None:
    class Container:
        @property
        def child(self):
            raise AttributeError("not initialized")

        @child.setter
        def child(self, value):
            self.stored_child = value

    root = Container()
    assert deep_get(root, ["child"], default=None, policy="attribute") is None
    deep_set(root, ["child", "value"], 3, policy="attribute")
    assert root.stored_child.value == 3


@pytest.mark.parametrize("template", [{}, None])
def test_incompatible_attribute_template_leaves_no_branch(template) -> None:
    root = SimpleNamespace()
    with pytest.raises(AttributeError):
        deep_set(root, ["new", "leaf"], 1, nullobject=template, policy="attribute")
    assert vars(root) == {}


def test_auto_preserves_list_bounds() -> None:
    root = SimpleNamespace(values=[])
    with pytest.raises(IndexError):
        deep_get(root, ["values", 0], policy="auto")
    assert deep_get(root, ["values", 0], default=None, policy="auto") is None
    with pytest.raises(IndexError):
        deep_set(root, ["values", 0, "name"], "Ada", policy="auto")
    assert root.values == []


@pytest.mark.parametrize("policy", ["unknown", "ITEM", None, 42])
def test_invalid_policy_fails_before_path_consumption(policy) -> None:
    def keys():
        pytest.fail("invalid policy must be rejected before consuming keys")
        yield "value"

    with pytest.raises(ValueError):
        deep_get({}, keys(), default=None, policy=policy)
    with pytest.raises(ValueError):
        deep_set({}, keys(), 1, policy=policy)


def test_policy_is_keyword_only() -> None:
    with pytest.raises(TypeError):
        deep_get({}, [], None, AccessPolicy.ITEM)
    with pytest.raises(TypeError):
        deep_set({}, ["a"], 1, {}, AccessPolicy.ITEM)
