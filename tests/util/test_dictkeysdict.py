from zuu.util.dictKeysDict import DictKeysDict, FrozenDict

class TestDictKeysDict:
    def test_init_and_getitem(self):
        d = DictKeysDict(
            {FrozenDict({"a": 1}): "value1", FrozenDict({"b": 2}): "value2"}
        )
        assert d[FrozenDict({"a": 1})] == "value1"
        assert d[FrozenDict({"b": 2})] == "value2"

    def test_setitem_and_update(self):
        d = DictKeysDict()
        d[FrozenDict({"c": 3})] = "value3"
        d.update({FrozenDict({"d": 4}): "value4"})
        assert d[FrozenDict({"c": 3})] == "value3"
        assert d[FrozenDict({"d": 4})] == "value4"

    def test_nested_dict_conversion(self):
        d = DictKeysDict({FrozenDict({"a": 1}): {"b": 2}})
        assert isinstance(d[FrozenDict({"a": 1})], dict)
        assert d[FrozenDict({"a": 1})]["b"] == 2

    def test_setdefault(self):
        d = DictKeysDict()
        result = d.setdefault(FrozenDict({"e": 5}), "value5")
        assert result == "value5"
        assert d[FrozenDict({"e": 5})] == "value5"

    def test_complex_nested_structure(self):
        complex_dict = {
            FrozenDict({"users": 1}): [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
            FrozenDict({"settings": 1}): {"theme": {"colors": {"primary": "#007bff"}}},
        }
        d = DictKeysDict(complex_dict)
        assert isinstance(d[FrozenDict({"users": 1})], list)
        assert isinstance(d[FrozenDict({"settings": 1})], dict)
        assert d[FrozenDict({"users": 1})][1]["name"] == "Bob"
        assert d[FrozenDict({"settings": 1})]["theme"]["colors"]["primary"] == "#007bff"

    def test_dict_key_preservation(self):
        key = FrozenDict({"x": 1, "y": 2})
        d = DictKeysDict({key: "value"})
        assert d[key] == "value"
        assert d[FrozenDict({"x": 1, "y": 2})] == "value"

    def test_dumpJson_and_loadJson_roundtrip(self):
        original = DictKeysDict(
            {FrozenDict({"a": 1}): [{"b": 2}, {FrozenDict({"c": 3}): "nested"}]}
        )
        json_str = DictKeysDict.dumpJson(original)
        loaded = DictKeysDict.loadJson(json_str)
        assert isinstance(loaded, DictKeysDict)
        assert loaded[FrozenDict({"a": 1})][1][FrozenDict({"c": 3})] == "nested"
