import pytest

from zuu.v202602_1.deep_dict import DeepDict
from zuu.v202602_1.deep_dict import DeepDictWrapper


def test_deep_get_returns_nested_value_for_dot_path() -> None:
    data = {"user": {"profile": {"name": "Zack"}}}

    assert DeepDict.deepGet(data, "user.profile.name") == "Zack"


def test_deep_get_returns_default_when_path_is_missing() -> None:
    data = {"user": {"profile": {}}}

    assert DeepDict.deepGet(data, "user.profile.name", "unknown") == "unknown"


def test_deep_set_creates_missing_dictionaries() -> None:
    data: dict[str, object] = {}

    DeepDict.deepSet(data, "settings.theme.name", "amber")

    assert data == {"settings": {"theme": {"name": "amber"}}}


def test_deep_set_replaces_non_dict_intermediate_value() -> None:
    data: dict[str, object] = {"settings": "legacy"}

    DeepDict.deepSet(data, "settings.theme.name", "amber")

    assert data == {"settings": {"theme": {"name": "amber"}}}


def test_deep_delete_removes_existing_key() -> None:
    data = {"user": {"profile": {"name": "Zack", "role": "admin"}}}

    deleted = DeepDict.deepDelete(data, ("user", "profile", "name"))

    assert deleted is True
    assert data == {"user": {"profile": {"role": "admin"}}}


def test_deep_delete_returns_false_for_missing_path() -> None:
    data = {"user": {"profile": {"role": "admin"}}}

    assert DeepDict.deepDelete(data, "user.profile.name") is False


def test_deep_update_merges_nested_mappings() -> None:
    data = {
        "user": {
            "profile": {"name": "Zack", "role": "admin"},
            "enabled": True,
        }
    }

    updated = DeepDict.deepUpdate(
        data,
        {
            "user": {
                "profile": {"role": "owner"},
                "enabled": False,
                "timezone": "UTC",
            }
        },
    )

    assert updated is data
    assert data == {
        "user": {
            "profile": {"name": "Zack", "role": "owner"},
            "enabled": False,
            "timezone": "UTC",
        }
    }


def test_wrapper_methods_delegate_to_wrapped_dict() -> None:
    data = {"user": {"profile": {"name": "Zack"}}}
    wrapped = DeepDictWrapper(data)

    assert wrapped.deepGet("user.profile.name") == "Zack"
    wrapped.deepSet("user.profile.role", "admin")
    wrapped.deepUpdate({"user": {"enabled": True}})

    assert wrapped.deepDelete("user.profile.name") is True
    assert data == {
        "user": {
            "profile": {"role": "admin"},
            "enabled": True,
        }
    }


@pytest.mark.parametrize("path", ["", [], ()])
def test_invalid_path_raises_value_error(path: object) -> None:
    with pytest.raises(ValueError):
        DeepDict.deepGet({}, path)  # type: ignore[arg-type]