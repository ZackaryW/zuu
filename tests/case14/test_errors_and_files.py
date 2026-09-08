import pytest

from zuu import case14
from zuu.case14 import YamlError, load, loads


@pytest.mark.parametrize(
    ("source", "line"),
    [
        (" a: 1", 1),
        ("a:\n\tb: 1", 2),
        ("-\tvalue", 1),
        ("a: 1\na: 2", 2),
        ("a: 1\n'a': 2", 2),
        ("123: value", 1),
        ("true: value", 1),
        (": value", 1),
        ("a: 1\n  b: 2", 2),
        ("a:\n   b: 1\n  c: 2", 3),
        ("a: 1\n- item", 2),
        ("- item\na: 1", 2),
        ("a: foo: bar", 1),
        ('a: "unclosed', 1),
        ("a: 'unclosed", 1),
        ('a: "closed" extra', 1),
        ("a: 'closed' extra", 1),
        ("a: [1, 2", 1),
        ("a: [1}", 1),
        ("a: [] extra", 1),
        ("a: [1]#comment", 1),
        ("---\na: 1", 1),
        ("a: 1\n...", 2),
        ("%YAML 1.2", 1),
        ("a: \x00", 1),
        ("a: \ud800", 1),
        ('a: "\\ud800"', 1),
        ("a:\n- item", 2),
    ],
)
def test_errors_include_source_line(source, line) -> None:
    with pytest.raises(YamlError) as error:
        loads(source)
    assert isinstance(error.value, ValueError)
    assert error.value.line == line
    assert str(error.value).startswith(f"line {line}:")


@pytest.mark.parametrize("source", [None, b"a: 1", {}, 1])
def test_loads_requires_text(source) -> None:
    with pytest.raises(TypeError, match="string"):
        loads(source)


def test_nesting_limit_is_reported_as_parser_error() -> None:
    source = "\n".join(" " * level + "key:" for level in range(101))
    with pytest.raises(YamlError, match="nesting exceeds"):
        loads(source)


def test_load_reads_path_and_encoding_without_modification(tmp_path) -> None:
    path = tmp_path / "pubspec.yaml"
    original = "name: café\nversion: 1.0.0".encode("utf-16")
    path.write_bytes(original)
    assert load(path, encoding="utf-16") == {"name": "café", "version": "1.0.0"}
    assert load(str(path), encoding="utf-16")["name"] == "café"
    assert path.read_bytes() == original
    with pytest.raises(UnicodeError):
        load(path)
    with pytest.raises(FileNotFoundError):
        load(tmp_path / "missing.yaml")


def test_load_utf8_and_parse_errors(tmp_path) -> None:
    path = tmp_path / "pubspec.yaml"
    path.write_text("name: café", encoding="utf-8")
    assert load(path) == {"name": "café"}
    path.write_text("name: a\nname: b", encoding="utf-8")
    with pytest.raises(YamlError) as error:
        load(path)
    assert error.value.line == 2


def test_case_metadata_and_exports() -> None:
    assert case14.__depends__ == ()
    assert "YAML" in case14.__purpose__
    assert case14.__all__ == ["loads", "load", "UnsupportedYaml", "YamlError"]
