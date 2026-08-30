import math

import pytest

from zuu.case8 import LayeredMapping, LayeredMappingError


def test_defaults_require_string_keys() -> None:
    with pytest.raises(LayeredMappingError, match="keys must be strings"):
        LayeredMapping({1: "value"})  # type: ignore[dict-item]


@pytest.mark.parametrize("value", [{1, 2}, math.nan, math.inf])
def test_final_mapping_must_be_strictly_json_compatible(value: object) -> None:
    with pytest.raises(LayeredMappingError, match="not JSON-compatible"):
        LayeredMapping({"value": value})


def test_custom_cast_results_are_checked_for_json_compatibility() -> None:
    with pytest.raises(LayeredMappingError, match="not JSON-compatible"):
        LayeredMapping(
            typed_assignments=["set+value=ignored"],
            casts={"set": lambda _: {1, 2}},
        )


@pytest.mark.parametrize(
    ("casts", "message"),
    [
        ({"bad-name": str}, "invalid cast name"),
        ({"valid": "not callable"}, "must be callable"),
    ],
)
def test_custom_cast_registry_is_validated(
    casts: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(LayeredMappingError, match=message):
        LayeredMapping(casts=casts)  # type: ignore[arg-type]
