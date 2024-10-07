from zuu.string import extract_fstring_keys

class TestExtractFstringKeys:
    def test_empty_string(self):
        assert extract_fstring_keys("") == []

    def test_string_without_fstring(self):
        assert extract_fstring_keys("Hello, world!") == []

    def test_single_key(self):
        assert extract_fstring_keys("Hello, {name}!") == ["name"]

    def test_multiple_keys(self):
        assert extract_fstring_keys("Hello, {first_name} {last_name}!") == [
            "first_name",
            "last_name",
        ]

    def test_repeated_keys(self):
        assert extract_fstring_keys("{key}, {key}, {key}") == ["key", "key", "key"]

    def test_nested_braces(self):
        assert extract_fstring_keys("{{not_a_key}}") == []

    def test_mixed_nested_and_valid(self):
        assert extract_fstring_keys("{{not_a_key}} {valid_key}") == ["valid_key"]

    def test_non_string_input(self):
        assert extract_fstring_keys(123) == []
        assert extract_fstring_keys(None) == []
        assert extract_fstring_keys([]) == []

    def test_invalid_fstring(self):
        assert extract_fstring_keys("{unclosed") == []

    def test_fstring_with_format_specifiers(self):
        assert extract_fstring_keys("{number:.2f}") == ["number"]

    def test_fstring_with_conversion_flags(self):
        assert extract_fstring_keys("{value!r}") == ["value"]
