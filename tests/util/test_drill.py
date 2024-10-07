import pytest
from zuu.trans import get_deep, set_deep, del_deep, set_default_deep

class TestDrillFunctions:
    @pytest.fixture
    def nested_dict(self):
        return {"a": {"b": {"c": 1, "d": [2, 3, 4]}}, "x": [{"y": 5}, {"z": 6}]}

    def test_get_deep_nested_dict(self, nested_dict):
        assert get_deep(nested_dict, "a", "b", "c") == 1
        assert get_deep(nested_dict, "a", "b", "d", 1) == 3
        assert get_deep(nested_dict, "x", 1, "z") == 6

    def test_get_deep_nonexistent_key(self, nested_dict):
        with pytest.raises(KeyError):
            get_deep(nested_dict, "a", "b", "e")

    def test_set_deep_nested_dict(self, nested_dict):
        set_deep(nested_dict, "a", "b", "c", value=10)
        assert nested_dict["a"]["b"]["c"] == 10

        set_deep(nested_dict, "x", 0, "y", value=15)
        assert nested_dict["x"][0]["y"] == 15

    def test_set_deep_new_key(self, nested_dict):
        set_deep(nested_dict, "a", "b", "e", value="new")
        assert nested_dict["a"]["b"]["e"] == "new"

    def test_del_deep_nested_dict(self, nested_dict):
        del_deep(nested_dict, "a", "b", "c")
        assert "c" not in nested_dict["a"]["b"]

        del_deep(nested_dict, "x", 0)
        assert len(nested_dict["x"]) == 1

    def test_del_deep_nonexistent_key(self, nested_dict):
        with pytest.raises(KeyError):
            del_deep(nested_dict, "a", "b", "e")

    def test_set_default_deep_existing_key(self, nested_dict):
        set_default_deep(nested_dict, "a", "b", "c", value=100)
        assert nested_dict["a"]["b"]["c"] == 1  # Original value remains

    def test_set_default_deep_new_key(self, nested_dict):
        set_default_deep(nested_dict, "a", "b", "e", value="default")
        assert nested_dict["a"]["b"]["e"] == "default"

    def test_set_default_deep_list_fillpadding(self, nested_dict):
        set_default_deep(nested_dict, "x", 3, value={"w": 7}, fillpadding=True)
        assert nested_dict["x"][3] == {"w": 7}
        assert nested_dict["x"][2] is None

    def test_set_default_deep_list_without_fillpadding(self, nested_dict):
        with pytest.raises(IndexError):
            set_default_deep(nested_dict, "x", 3, value={"w": 7}, fillpadding=False)

    def test_set_default_deep_set(self):
        nested_set = {"a": {1, 2, 3}}
        with pytest.raises(IndexError):
            set_default_deep(nested_set, "a", 0, value=4)


class TestComplexDataStructures:
    @pytest.fixture
    def complex_data(self):
        return {
            "users": [
                {
                    "name": "Alice",
                    "details": {
                        "age": 30,
                        "hobbies": ["reading", "swimming"],
                        "address": {"street": "123 Main St", "city": "Wonderland"},
                    },
                },
                {
                    "name": "Bob",
                    "details": {
                        "age": 25,
                        "hobbies": ["gaming", "cooking"],
                        "address": {"street": "456 Elm St", "city": "Dreamland"},
                    },
                },
            ],
            "products": [
                {
                    "name": "Laptop",
                    "specs": {
                        "brand": "TechCo",
                        "components": [
                            {
                                "type": "CPU",
                                "details": {"model": "i7", "speed": "3.2GHz"},
                            },
                            {
                                "type": "RAM",
                                "details": {"size": "16GB", "type": "DDR4"},
                            },
                        ],
                    },
                }
            ],
            "settings": {
                "theme": {
                    "colors": {"primary": "#007bff", "secondary": "#6c757d"},
                    "fonts": ["Arial", "Helvetica", "sans-serif"],
                }
            },
        }

    def test_get_deep_complex(self, complex_data):
        assert get_deep(complex_data, "users", 0, "name") == "Alice"
        assert get_deep(complex_data, "users", 1, "details", "hobbies", 1) == "cooking"
        assert (
            get_deep(
                complex_data, "products", 0, "specs", "components", 1, "details", "size"
            )
            == "16GB"
        )

    def test_set_deep_complex(self, complex_data):
        set_deep(complex_data, "users", 0, "details", "age", value=31)
        assert complex_data["users"][0]["details"]["age"] == 31

        set_deep(
            complex_data, "settings", "theme", "colors", "tertiary", value="#28a745"
        )
        assert complex_data["settings"]["theme"]["colors"]["tertiary"] == "#28a745"

    def test_del_deep_complex(self, complex_data):
        del_deep(complex_data, "users", 1, "details", "hobbies", 0)
        assert complex_data["users"][1]["details"]["hobbies"] == ["cooking"]

        del_deep(complex_data, "products", 0, "specs", "components", 1)
        assert len(complex_data["products"][0]["specs"]["components"]) == 1

    def test_set_default_deep_complex(self, complex_data):
        set_default_deep(
            complex_data, "users", 2, value={"name": "Charlie"}, fillpadding=True
        )
        assert complex_data["users"][2]["name"] == "Charlie"

        set_default_deep(complex_data, "settings", "notifications", "email", value=True)
        assert complex_data["settings"]["notifications"]["email"] is True

    def test_complex_operations(self, complex_data):
        # Combine multiple operations
        set_deep(complex_data, "users", 0, "details", "hobbies", 2, value="painting")
        del_deep(complex_data, "products", 0, "specs", "brand")
        set_default_deep(
            complex_data,
            "settings",
            "theme",
            "animations",
            value={"enabled": True, "duration": "0.3s"},
        )

        assert get_deep(complex_data, "users", 0, "details", "hobbies", 2) == "painting"
        with pytest.raises(KeyError):
            get_deep(complex_data, "products", 0, "specs", "brand")
        assert (
            get_deep(complex_data, "settings", "theme", "animations", "duration")
            == "0.3s"
        )
