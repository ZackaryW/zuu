from zuu.case14 import UnsupportedYaml, loads


def test_pubspec_dependencies_assets_and_fonts() -> None:
    result = loads("""\
name: sample_app
description: A small application. # ordinary comment
publish_to: 'none'
version: 1.2.3+4
environment:
  sdk: '>=3.2.0 <4.0.0'
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.0
  local_package:
    path: ../local_package
  git_package:
    git:
      url: https://example.test/repo.git#main
      ref: main
dev_dependencies:
  flutter_test:
    sdk: flutter
dependency_overrides:
  http: any
flutter:
  uses-material-design: true
  assets:
    - assets/images/
    - assets/icon.png
  fonts:
    - family: Example Font
      fonts:
        - asset: fonts/regular.ttf
        - asset: fonts/bold.ttf
          weight: 700
          style: italic
platforms:
  android:
""")
    assert result == {
        "name": "sample_app",
        "description": "A small application.",
        "publish_to": "none",
        "version": "1.2.3+4",
        "environment": {"sdk": ">=3.2.0 <4.0.0"},
        "dependencies": {
            "flutter": {"sdk": "flutter"},
            "http": "^1.2.0",
            "local_package": {"path": "../local_package"},
            "git_package": {
                "git": {"url": "https://example.test/repo.git#main", "ref": "main"}
            },
        },
        "dev_dependencies": {"flutter_test": {"sdk": "flutter"}},
        "dependency_overrides": {"http": "any"},
        "flutter": {
            "uses-material-design": True,
            "assets": ["assets/images/", "assets/icon.png"],
            "fonts": [
                {
                    "family": "Example Font",
                    "fonts": [
                        {"asset": "fonts/regular.ttf"},
                        {"asset": "fonts/bold.ttf", "weight": 700, "style": "italic"},
                    ],
                }
            ],
        },
        "platforms": {"android": None},
    }


def test_folded_description_does_not_hide_dependencies() -> None:
    result = loads("""\
name: example
description: >- # retain the original scalar
  A long description with a colon: and an unmatched " quote.
  # This is scalar content, not a YAML comment.

  Another paragraph.
dependencies:
  example: ^1.0.0
""")
    assert result["description"] == UnsupportedYaml(
        ">- # retain the original scalar\n"
        '  A long description with a colon: and an unmatched " quote.\n'
        "  # This is scalar content, not a YAML comment.\n\n"
        "  Another paragraph."
    )
    assert result["dependencies"] == {"example": "^1.0.0"}


def test_empty_values_and_nested_lists() -> None:
    assert loads("-\n- null\n- - first\n  - second\n- key:\n    nested: []") == [
        None,
        None,
        ["first", "second"],
        {"key": {"nested": []}},
    ]


def test_mapping_order_and_literal_keys() -> None:
    result = loads("'a:b': first\n'': empty key\n'123': numeric key\na.b: last")
    assert list(result.items()) == [
        ("a:b", "first"),
        ("", "empty key"),
        ("123", "numeric key"),
        ("a.b", "last"),
    ]


def test_indentation_width_is_not_fixed() -> None:
    assert loads("parent:\n child:\n     value: 1\n sibling: 2\nlast: 3") == {
        "parent": {"child": {"value": 1}, "sibling": 2},
        "last": 3,
    }
