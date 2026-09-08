import pytest

from zuu.case14 import loads


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("", None),
        ("# comment\n\n", None),
        ("null", None),
        ("Null", None),
        ("NULL", None),
        ("~", None),
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("0", 0),
        ("-12", -12),
        ("+12", 12),
        ("0012", 12),
        ("1.5", 1.5),
        (".5", 0.5),
        ("1.", 1.0),
        ("-2e3", -2000.0),
        ("yes", "yes"),
        ("on", "on"),
        ("2026-09-08", "2026-09-08"),
        ("1.0.0+1", "1.0.0+1"),
        ("^3.2.0", "^3.2.0"),
        ("https://example.test/a#part", "https://example.test/a#part"),
        ("it's plain # comment", "it's plain"),
        ("'it''s # quoted' # comment", "it's # quoted"),
        ('"true"', "true"),
        ('"a: b # c" # comment', "a: b # c"),
        (r'"a\nb\t\u263a"', "a\nb\t☺"),
        (r"'C:\path'", r"C:\path"),
        ("[]", []),
        ("{} # empty map", {}),
        ('""', ""),
    ],
)
def test_scalar_values(source, expected) -> None:
    result = loads(source)
    assert result == expected
    assert type(result) is type(expected)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_line_endings_bom_and_unicode(newline) -> None:
    assert loads("\ufeff" + newline.join(["name: café", "value: 世界"])) == {
        "name": "café",
        "value": "世界",
    }


def test_calls_return_independent_containers() -> None:
    first = loads("items: []")
    first["items"].append(1)
    assert loads("items: []") == {"items": []}
