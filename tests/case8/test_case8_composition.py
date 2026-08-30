from types import MappingProxyType

import pytest

from zuu.case8 import LayeredMapping, LayeredMappingError


def test_layers_apply_in_declared_precedence_without_recursive_merge() -> None:
    defaults = {"host": "localhost", "nested": {"default": True}, "port": 80}

    result = LayeredMapping(
        defaults,
        json_maps=['{"port": 8080, "nested": {"map": true}}'],
        assignments=["host=example.test", "token=a=b=c"],
        typed_assignments=["int+port=9000", "bool+secure=true"],
    )

    assert dict(result) == {
        "host": "example.test",
        "nested": {"map": True},
        "port": 9000,
        "token": "a=b=c",
        "secure": True,
    }
    assert defaults == {
        "host": "localhost",
        "nested": {"default": True},
        "port": 80,
    }


def test_multiple_layers_are_ordered_and_empty_layers_are_supported() -> None:
    result = LayeredMapping(
        json_maps=['{"value": 1}', '{"value": 2}'],
        assignments=(),
        typed_assignments=(),
    )

    assert result == {"value": 2}
    assert LayeredMapping() == {}


def test_result_is_a_read_only_mapping_with_an_independent_copy() -> None:
    result = LayeredMapping({"value": 1})

    assert isinstance(result.values, MappingProxyType)
    with pytest.raises(TypeError):
        result.values["value"] = 2  # type: ignore[index]

    copy = result.to_dict()
    copy["value"] = 3
    assert result["value"] == 1
    assert repr(result) == "LayeredMapping({'value': 1})"


@pytest.mark.parametrize(
    ("assignment", "expected"),
    [
        ("str+value=12", "12"),
        ("int+value=12", 12),
        ("float+value=1.25", 1.25),
        ("bool+value=true", True),
        ("bool+value=false", False),
        ('json+value={"nested":[1,true]}', {"nested": [1, True]}),
    ],
)
def test_builtin_casts_preserve_typed_values(
    assignment: str,
    expected: object,
) -> None:
    assert LayeredMapping(typed_assignments=[assignment])["value"] == expected


def test_custom_casts_extend_and_can_override_the_registry() -> None:
    result = LayeredMapping(
        typed_assignments=["upper+name=zuu", "bool+enabled=yes"],
        casts={"upper": str.upper, "bool": lambda value: value == "yes"},
    )

    assert result == {"name": "ZUU", "enabled": True}


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"json_maps": ["{"]}, "invalid JSON mapping"),
        ({"json_maps": ["[1, 2]"]}, "root"),
        ({"assignments": ["missing"]}, "key=value"),
        ({"assignments": ["bad key=value"]}, "invalid assignment key"),
        ({"typed_assignments": ["int=value"]}, r"type\+key=value"),
        ({"typed_assignments": ["unknown+value=1"]}, "unknown cast"),
        ({"typed_assignments": ["int+value=nope"]}, "cast 'int' failed"),
        ({"typed_assignments": ["bool+value=True"]}, "expected exactly"),
    ],
)
def test_invalid_layers_raise_a_contextual_error(
    arguments: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(LayeredMappingError, match=message):
        LayeredMapping(**arguments)  # type: ignore[arg-type]
