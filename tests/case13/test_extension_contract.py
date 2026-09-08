import pytest

from zuu.case13 import deep_has, deep_pop, deep_setdefault, deep_update


@pytest.fixture(params=[deep_has, deep_pop, deep_setdefault, deep_update])
def operation(request):
    function = request.param

    def invoke(root, keys, **kwargs):
        if function is deep_update:
            return function(root, keys, lambda value: value, **kwargs)
        return function(root, keys, **kwargs)

    return invoke


@pytest.mark.parametrize("keys", ["abc", b"abc", None, 3])
def test_extensions_reject_invalid_paths(operation, keys) -> None:
    root = {}
    with pytest.raises(TypeError):
        operation(root, keys)
    assert root == {}


def test_extensions_validate_policy_before_path_consumption(operation) -> None:
    def keys():
        pytest.fail("invalid policy consumed keys")
        yield "value"

    with pytest.raises(ValueError):
        operation({}, keys(), policy="invalid")


def test_extensions_consume_path_before_mutation(operation) -> None:
    root = {"value": 1}

    def keys():
        yield "value"
        raise RuntimeError("path failed")

    with pytest.raises(RuntimeError, match="path failed"):
        operation(root, keys())
    assert root == {"value": 1}


@pytest.mark.parametrize("operation", [deep_setdefault, deep_update])
def test_new_writes_reject_empty_paths(operation) -> None:
    with pytest.raises(ValueError, match="at least one key"):
        if operation is deep_update:
            operation({}, [], lambda value: value)
        else:
            operation({}, [])


def test_update_requires_a_callable_before_consuming_path() -> None:
    def keys():
        pytest.fail("invalid transform consumed keys")
        yield "value"

    with pytest.raises(TypeError, match="callable"):
        deep_update({}, keys(), None)
