# case14: Simple YAML reader

Case 14 reads common configuration structures, with `pubspec.yaml` as the main
use case. It uses only the standard library and has no case dependencies.
It has no writer and does not implement the full YAML language or validate the
pubspec schema.

```python
from zuu.case14 import load, loads, UnsupportedYaml

config = loads("""\
name: example_app
version: 1.2.3+4
environment:
  sdk: '^3.2.0'
dependencies:
  flutter:
    sdk: flutter
flutter:
  uses-material-design: true
  assets:
    - assets/images/
description: >-
  A description that is preserved without interpreting YAML folding.
""")

assert config["dependencies"]["flutter"]["sdk"] == "flutter"
assert config["flutter"]["assets"] == ["assets/images/"]
assert isinstance(config["description"], UnsupportedYaml)
assert config["description"].raw.startswith(">-")

# Read an existing file; strings here are paths, not YAML content.
# config = load("pubspec.yaml")
```

The supported structures cover dependency declarations, environment constraints,
asset lists, and lists of font mappings like those in the
[Dart pubspec guide](https://dart.dev/tools/pub/pubspec) and
[Flutter pubspec guide](https://docs.flutter.dev/tools/pubspec).
Version strings and constraints such as `1.2.3+4`, `^3.2.0`, and quoted
`'>=3.2.0 <4.0.0'` remain strings.

## API

| Export | Behavior |
|--------|----------|
| `loads(text)` | Parse a string into dictionaries, lists, scalar values, and `UnsupportedYaml` objects. Empty or comment-only input returns `None`. |
| `load(path, *, encoding="utf-8")` | Read a string or path-like file path and call `loads`. Files are never modified. I/O and decoding errors propagate. |
| `UnsupportedYaml(raw)` | Immutable wrapper containing the uninterpreted value fragment. Compare wrappers by value or access `.raw`. |
| `YamlError` | A `ValueError` subclass with a one-based `.line` attribute and a line-numbered error message. |

## Parsed subset

- Space-indented mappings with string keys and `key: value` syntax. Sibling
  indentation must agree; the root starts at column one. Nesting may use any
  positive number of spaces. Quoted keys can contain colons or be empty.
- Block lists using `- value`, including compact mappings such as
  `- family: Example Font` followed by additional indented fields, and nested lists.
- Empty mapping values and bare list entries become `None` unless they have a
  nested block. Empty `[]` and `{}` are supported.
- Plain strings, single-quoted strings with doubled apostrophes, and double-quoted
  strings using JSON escapes. Comments start at `#` outside quotes when preceded
  by whitespace or at the start of a line. URL fragments such as `repo.git#main`
  remain part of the value.
- Null (`null`, `Null`, `NULL`, `~`), booleans (`true`/`false` in lowercase,
  title case, or uppercase), signed decimal integers, and decimal floats with
  optional exponents. Leading-zero decimal integers are read as decimal.
  Quoting prevents conversion. `yes`, `on`, and date-like text remain strings.
- UTF-8 by default, an optional initial BOM, and LF, CRLF, or CR line endings.
  `load` accepts an explicit encoding.

Dictionaries retain input order, and each parse creates independent containers.
There is no schema registration, callback mechanism, or dependency resolution.

## Unsupported values

The reader preserves these as `UnsupportedYaml` while continuing with sibling fields:

- Literal and folded blocks (`|`, `>`, including their modifiers) and their indented bodies.
- Nonempty flow collections (`[a, b]`, `{a: b}`), including multiline collections.
- Anchors, aliases, and tags beginning with `&`, `*`, or `!`, plus indented bodies.
- Multiline quoted strings and closed double-quoted strings whose escapes cannot
  be decoded by the JSON string reader.
- Base-prefixed numeric forms and special floats such as `0xFF`, `0o77`, and `.inf`.

For example, `copy: *base` remains an opaque alias. A `<<: *base` entry is retained
under the literal key `<<`; no merge is performed. An anchored mapping is itself
opaque, so its children are not exposed as a parsed dictionary.

Opaque fragments omit the owning mapping key or list dash. Multiline fragments
retain body indentation, comments, and blank lines, with newlines normalized to LF.
These fragments are for inspection, not a lossless document editing format;
surrounding separators and ordinary scalar comments are not retained.

The reader locates an opaque value's boundary but does not validate its contents.
For example, duplicate keys inside an opaque flow mapping are not inspected.
Flow values must have balanced delimiters, and multiline quotes must close.
Tagged or anchored bodies are delimited by indentation; complex combinations
whose boundaries cannot be located this way can still raise `YamlError`.

## Errors and limits

Malformed supported syntax raises `YamlError`, including duplicate mapping keys,
unexpected indentation, mixed mapping/list blocks, non-string keys, unterminated
quotes or flow collections, and extra text following quoted or flow values.
Tabs cannot be used for indentation. Nesting is limited to 100 parsed nodes along
a branch, and Python's integer conversion limit applies.

Document markers (`---`, `...`), directives, complex keys, and indentless sequences
are outside the supported document structure and raise errors. Multiline plain
strings are also unsupported; use a quoted or `|`/`>` value to preserve them as
opaque text. There is no claim of complete YAML 1.2 conformance or acceptance of
every valid pubspec spelling.

## Tests

The larger, fictional samples are available as readable YAML files:

| Sample | Coverage |
|--------|----------|
| [Application pubspec](../../tests/case14/samples/application_pubspec.yaml) | Dependencies, fonts, assets, nested lists, and mixed scalar values across 131 lines. |
| [Mixed configuration](../../tests/case14/samples/mixed_configuration.yaml) | 115 lines combining parsed fields with opaque blocks, flow collections, anchors, tags, and multiline quotes. |
| [Service configuration](../../tests/case14/samples/service_configuration.yaml) | 100 lines of listeners, routes, storage, retries, logging, and feature settings. |
| [Inventory sequence](../../tests/case14/samples/inventory_sequence.yaml) | An 89-line root list containing contacts, bins, items, matrices, and audit records. |

Tests compare each entire parsed tree with an independently specified expected
result, through both `loads` and `load`, with LF and CRLF inputs. They also check
that file reads leave the source unchanged and that errors after large valid
sections retain their source line numbers.

Generated samples exercise a 4,507-line configuration, a 4,800-line root sequence
with 600 independent records, and 40 nested mapping/list pairs with siblings at
every level. These are correctness checks, not timing benchmarks.

```powershell
uv run pytest -q tests/case14
```
