from pathlib import Path

import pytest

from zuu.case14 import UnsupportedYaml, YamlError, load, loads

SAMPLES = Path(__file__).with_name("samples")


def application_expected():
    return {
        "name": "trail_atlas",
        "version": "2.4.1+37",
        "description": "Maps, field notes, and offline routes for walking trips.",
        "publish_to": "none",
        "homepage": "https://example.test/trail-atlas",
        "repository": "https://example.test/source/trail-atlas#main",
        "issue_tracker": "https://example.test/source/trail-atlas/issues",
        "environment": {"sdk": ">=3.2.0 <4.0.0", "flutter": ">=3.16.0"},
        "dependencies": {
            "flutter": {"sdk": "flutter"},
            "flutter_localizations": {"sdk": "flutter"},
            "atlas_network": "^2.1.0",
            "atlas_storage": "^3.0.2",
            "atlas_logging": "any",
            "atlas_models": {"path": "../atlas_models"},
            "atlas_widgets": {
                "git": {
                    "url": "https://example.test/source/widgets.git",
                    "ref": "stable",
                    "path": "packages/widgets",
                }
            },
            "atlas_tiles": {
                "hosted": {
                    "name": "atlas_tiles",
                    "url": "https://packages.example.test",
                },
                "version": "^1.5.0",
            },
            "atlas_optional": None,
        },
        "dev_dependencies": {
            "flutter_test": {"sdk": "flutter"},
            "integration_test": {"sdk": "flutter"},
            "atlas_lints": "^1.0.0",
            "atlas_codegen": {"path": "tools/codegen"},
        },
        "dependency_overrides": {"atlas_storage": {"path": "../storage_patch"}},
        "flutter": {
            "uses-material-design": True,
            "generate": True,
            "assets": [
                "assets/images/",
                "assets/icons/compass.png",
                "assets/maps/europe.json",
                "assets/maps/asia.json",
                "assets/data/places.csv",
                "assets/labels/route #1.txt",
                "assets/legal/privacy.txt",
                "assets/audio/arrival.wav",
            ],
            "shaders": ["shaders/terrain.frag", "shaders/water.frag"],
            "fonts": [
                {
                    "family": "Atlas Sans",
                    "fonts": [
                        {"asset": "fonts/AtlasSans-Regular.ttf", "weight": 400},
                        {"asset": "fonts/AtlasSans-Bold.ttf", "weight": 700},
                        {"asset": "fonts/AtlasSans-Italic.ttf", "style": "italic"},
                    ],
                },
                {
                    "family": "Atlas Mono",
                    "fonts": [
                        {"asset": "fonts/AtlasMono-Regular.ttf"},
                        {"asset": "fonts/AtlasMono-Medium.ttf", "weight": 500},
                    ],
                },
            ],
            "deferred-components": [
                {
                    "name": "mountain_maps",
                    "libraries": [
                        "package:trail_atlas/mountains.dart",
                        "package:trail_atlas/elevation.dart",
                    ],
                    "assets": ["assets/maps/mountains/"],
                },
                {
                    "name": "coastal_maps",
                    "libraries": ["package:trail_atlas/coasts.dart"],
                    "assets": [],
                },
            ],
        },
        "platforms": dict.fromkeys(
            ["android", "ios", "linux", "macos", "windows", "web"]
        ),
        "topics": ["maps", "walking", "offline"],
        "screenshots": [
            {
                "description": "Map: mountain trails",
                "path": "screenshots/mountains.png",
            },
            {"description": "Day's notes #2", "path": "screenshots/notes.png"},
        ],
        "funding": [
            "https://example.test/sponsor",
            "https://example.test/donate#atlas",
        ],
        "executables": {"atlas_import": "import_routes", "atlas_inspect": None},
        "atlas_settings": {
            "enabled": True,
            "telemetry": False,
            "retries": 3,
            "timeout": 2.5,
            "title": "Explorer's atlas",
            "empty_label": "",
            "cache": {},
            "fallback": None,
            "matrix": [[1, 2], [3, 4]],
            "labels": {
                "123": "numeric-looking key",
                "a:b": "colon key",
                "release.channel": "stable",
                "": "empty key",
            },
        },
        "final_marker": "complete",
    }


def mixed_expected():
    return {
        "name": "field_station",
        "description": UnsupportedYaml(
            ">- # keep folded text uninterpreted\n"
            "  Collect observations from remote stations.\n"
            "  Text can contain keys: values, # signs, and an unmatched ' quote.\n\n"
            "  This paragraph belongs to the same description."
        ),
        "version": "5.2.0+11",
        "environment": {"sdk": "^3.2.0"},
        "dependencies": {
            "station_core": "^1.0.0",
            "station_protocol": {"path": "../protocol"},
        },
        "station_defaults": UnsupportedYaml(
            "&defaults\n  retries: 3\n  options:\n    transport: radio\n"
            "    # Opaque bodies are not traversed as mappings.\n    channels: [north, south]"
        ),
        "station_profile": {
            "<<": UnsupportedYaml("*defaults"),
            "name": "alpine",
            "enabled": True,
            "location": UnsupportedYaml("!coordinates 45.2, 6.1"),
            "altitude": 2100,
        },
        "routes": [
            {
                "name": "primary",
                "options": UnsupportedYaml("{retries: 3, timeout: 1.5}"),
                "enabled": True,
                "labels": UnsupportedYaml(
                    "[uplink, \"payload ] intact\", 'operator''s {notes}']"
                ),
                "target": "radio://north.example.test/channel#main",
            },
            {
                "name": "secondary",
                "options": UnsupportedYaml(
                    '{\n      retries: 5,\n      nested: [one, {message: "a } bracket"}], # comment contains ] }\n'
                    "      quoted: 'it''s still inside'\n    }"
                ),
                "enabled": False,
                "labels": [],
                "target": "radio://south.example.test/channel",
            },
            {
                "name": "manual",
                "instructions": UnsupportedYaml(
                    "|-\n      Step 1: attach the antenna.\n"
                    "      # This line belongs to the instructions.\n"
                    "      - This dash is text, not a list item.\n      Step 2: select a station."
                ),
                "enabled": True,
                "target": "manual",
            },
        ],
        "display": {
            "title": "Field\nStation",
            "subtitle": "Operator's console",
            "notice": UnsupportedYaml(
                '"First line of an opaque quoted value\n    second line with a # and a ] character"'
            ),
            "theme": "dark",
            "footnote": UnsupportedYaml(
                "'Another multiline\n    value with doubled '' apostrophes'"
            ),
            "show_clock": True,
            "unicode_escape": UnsupportedYaml(r'"\N\x41"'),
            "refresh_seconds": 1.25,
        },
        "diagnostics": {
            "mask": UnsupportedYaml("0xFF"),
            "unlimited": UnsupportedYaml(".inf"),
            "missing": UnsupportedYaml(".NaN"),
            "attempts": 0,
            "enabled": False,
            "last_error": None,
            "message": "no",
        },
        "pipeline": [
            {
                "stage": "receive",
                "transforms": [
                    UnsupportedYaml("[strip, normalize]"),
                    {
                        "name": "decode",
                        "settings": UnsupportedYaml(
                            "!decoder\n          format: station-v2\n          headers: [timestamp, payload]"
                        ),
                        "strict": True,
                    },
                ],
                "next": "validate",
            },
            {
                "stage": "validate",
                "rules": [
                    {"name": "range", "minimum": -12.5, "maximum": 1000.0},
                    {
                        "name": "quality",
                        "allowed": UnsupportedYaml("[good, excellent]"),
                        "required": True,
                    },
                ],
                "next": "store",
            },
            {"stage": "store", "rules": [], "next": None},
        ],
        "documents": [
            UnsupportedYaml("|+\n    First document.\n\n    Last paragraph."),
            {
                "label": "index",
                "body": UnsupportedYaml(
                    ">\n      An opaque body nested in a compact mapping.\n      The sibling key remains readable."
                ),
                "revision": 2,
            },
            "finished",
        ],
        "summary": {
            "station_count": 3,
            "route_names": ["primary", "secondary", "manual"],
            "metadata": {},
        },
        "final_marker": "complete",
    }


@pytest.fixture(params=["application_pubspec", "mixed_configuration"])
def large_sample(request, tmp_path):
    # Keep all files exercised by load() in the temporary test directory.
    text = (SAMPLES / f"{request.param}.yaml").read_text(encoding="utf-8")
    expected = (
        application_expected()
        if request.param == "application_pubspec"
        else mixed_expected()
    )
    return text, expected, tmp_path / "pubspec.yaml"


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_large_samples_match_complete_expected_trees(large_sample, newline) -> None:
    text, expected, path = large_sample
    content = text.replace("\n", newline)
    assert loads(content) == expected
    path.write_bytes(content.encode("utf-8"))
    assert load(path) == expected
    assert path.read_bytes() == content.encode("utf-8")


@pytest.mark.parametrize("suffix", ["name: duplicate\n", "  misplaced: true\n"])
def test_large_samples_report_errors_after_all_valid_sections(
    large_sample, suffix
) -> None:
    text, _, path = large_sample
    broken = text + suffix
    path.write_text(broken, encoding="utf-8")
    for read in (lambda: loads(broken), lambda: load(path)):
        with pytest.raises(YamlError) as error:
            read()
        assert error.value.line == len(text.splitlines()) + 1


def test_thousands_of_lines_preserve_all_entries_and_late_errors() -> None:
    lines = ["name: large_workspace", "dependencies:"]
    dependencies = {}
    for index in range(1000):
        lines.extend([f"  package_{index}:", f"    path: packages/package_{index}"])
        dependencies[f"package_{index}"] = {"path": f"packages/package_{index}"}
    lines.extend(["flutter:", "  assets:"])
    assets = [f"assets/image_{index}.png" for index in range(1000)]
    lines.extend(f"    - {asset}" for asset in assets)
    lines.append("  fonts:")
    fonts = []
    for index in range(250):
        lines.extend(
            [
                f"    - family: Family {index}",
                "      fonts:",
                f"        - asset: fonts/family_{index}.ttf",
                "          weight: 400",
                f"        - asset: fonts/family_{index}_bold.ttf",
                "          weight: 700",
            ]
        )
        fonts.append(
            {
                "family": f"Family {index}",
                "fonts": [
                    {"asset": f"fonts/family_{index}.ttf", "weight": 400},
                    {"asset": f"fonts/family_{index}_bold.ttf", "weight": 700},
                ],
            }
        )
    lines.extend(["metadata: {generated: true}", "final_marker: complete"])
    text = "\n".join(lines)
    result = loads(text)
    assert result == {
        "name": "large_workspace",
        "dependencies": dependencies,
        "flutter": {"assets": assets, "fonts": fonts},
        "metadata": UnsupportedYaml("{generated: true}"),
        "final_marker": "complete",
    }
    assert list(result["dependencies"]) == list(dependencies)
    with pytest.raises(YamlError) as error:
        loads(text + "\nname: duplicate")
    assert error.value.line == len(lines) + 1
