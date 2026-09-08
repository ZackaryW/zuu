from pathlib import Path

import pytest

from zuu.case14 import UnsupportedYaml, YamlError, load, loads

SAMPLES = Path(__file__).with_name("samples")


def service_expected():
    return {
        "application": {
            "name": "observation_gateway",
            "display_name": "Observer's gateway",
            "revision": 12,
            "enabled": True,
            "maintenance": False,
            "banner": "Welcome\nChoose a station",
            "empty_message": "",
            "started_at": "2026-09-08",
        },
        "listeners": [
            {
                "name": "public",
                "address": "0.0.0.0",
                "port": 8080,
                "tls": {"enabled": False, "certificate": None},
                "headers": {"X-Trace:Mode": "verbose", "Cache-Control": "no-cache"},
                "routes": [
                    {"path": "/health", "methods": ["GET"], "timeout": 0.5},
                    {
                        "path": "/observations",
                        "methods": ["GET", "POST"],
                        "timeout": 20.0,
                    },
                ],
            },
            {
                "name": "admin",
                "address": "127.0.0.1",
                "port": 9090,
                "tls": {"enabled": True, "certificate": "/etc/gateway/admin.pem"},
                "headers": {},
                "routes": [],
            },
        ],
        "storage": {
            "primary": {
                "host": "database.internal",
                "port": 5432,
                "database": "observations",
                "credentials": {
                    "username": "service_account",
                    "password": UnsupportedYaml("!env GATEWAY_PASSWORD"),
                },
                "pool": {"minimum": 2, "maximum": 24, "idle_seconds": 30.0},
            },
            "replicas": [
                {"host": "replica_a.internal", "weight": 2},
                {"host": "replica_b.internal", "weight": 1},
            ],
            "cache": {"backend": "memory", "capacity": 4096, "prefix": "gateway:v2"},
        },
        "retry": {
            "attempts": 4,
            "delays": [0.25, 0.5, 1.0, 2.0],
            "jitter": True,
            "status_codes": UnsupportedYaml("[429, 502, 503]"),
        },
        "logging": {
            "level": "info",
            "sinks": [
                {"kind": "stderr", "format": "text"},
                {
                    "kind": "file",
                    "filename": "/var/log/gateway.log",
                    "rotate": {"count": 7, "size": 1048576},
                },
            ],
            "template": UnsupportedYaml(
                "|-\n    timestamp: ${timestamp}\n    message: ${message}\n    # Preserve this template line."
            ),
            "include_source": False,
        },
        "features": {
            "true": "boolean-looking string key",
            "01": "numeric-looking string key",
            "sensor.v2": True,
            "optional": None,
            "labels": ["alpha", "route #3", "value: with a colon"],
        },
        "shutdown": {"grace_seconds": 5, "drain": True, "hook": None},
    }


def inventory_expected():
    return [
        {
            "id": "north_depot",
            "title": "North depot",
            "active": True,
            "coordinates": {"latitude": 51.5, "longitude": -0.12},
            "contacts": [
                {
                    "name": "Alex",
                    "roles": ["manager", "receiving"],
                    "channels": {
                        "email": "alex@example.test",
                        "phone": "+44 000 000 000",
                    },
                },
                {"name": "Sam", "roles": ["dispatch"], "channels": {}},
            ],
            "bins": [
                {
                    "label": "A-01",
                    "capacity": 100,
                    "items": [
                        {"sku": "00123", "count": 12, "unit_price": 4.5, "flags": []},
                        {
                            "sku": "cable_blue",
                            "count": 0,
                            "unit_price": 0.75,
                            "flags": ["reorder"],
                        },
                    ],
                },
                {"label": "A-02", "capacity": 50, "items": []},
            ],
            "transfer_costs": [[0, 2.5], [2.5, 0]],
            "note": UnsupportedYaml(
                ">-\n    Loading bay opens at 08:00.\n    Use entrance B: the west gate is closed."
            ),
            "audit": {"last_count": "2026-09-01", "approved": True, "exception": None},
        },
        {
            "id": "south_depot",
            "title": "South: receiving",
            "active": False,
            "coordinates": {"latitude": -33.9, "longitude": 18.4},
            "contacts": [],
            "bins": [
                {
                    "label": "B-01",
                    "capacity": 200,
                    "items": [
                        {
                            "sku": "panel",
                            "count": 25,
                            "unit_price": 19.95,
                            "flags": ["fragile", "indoors"],
                        },
                    ],
                }
            ],
            "transfer_costs": [],
            "note": "Renovation #2",
            "audit": {
                "last_count": None,
                "approved": False,
                "exception": UnsupportedYaml("{reason: renovation, review: pending}"),
            },
        },
        {
            "id": "mobile_unit",
            "title": "Mobile unit",
            "active": True,
            "coordinates": None,
            "contacts": [
                {
                    "name": "Lee",
                    "roles": ["driver"],
                    "channels": {"radio": "dispatch://channel/7#mobile"},
                }
            ],
            "bins": [],
            "transfer_costs": [],
            "note": "",
            "audit": {"last_count": "2026-09-07", "approved": True, "exception": None},
        },
    ]


@pytest.mark.parametrize(
    ("sample", "expected_factory"),
    [
        ("service_configuration", service_expected),
        ("inventory_sequence", inventory_expected),
    ],
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_general_documents_match_complete_expected_trees(
    tmp_path, sample, expected_factory, newline
) -> None:
    text = (
        (SAMPLES / f"{sample}.yaml").read_text(encoding="utf-8").replace("\n", newline)
    )
    expected = expected_factory()
    assert loads(text) == expected
    path = tmp_path / "configuration.yaml"
    path.write_bytes(text.encode("utf-8"))
    assert load(path) == expected
    assert path.read_bytes() == text.encode("utf-8")


def test_deep_alternating_mappings_and_sequences() -> None:
    # Exercise repeated descent and return from list/mapping pairs near the
    # documented nesting limit, including a sibling at every mapping level.
    text = "value: leaf\nempty: []\n"
    expected = {"value": "leaf", "empty": []}
    for level in reversed(range(40)):
        indented = "\n".join("    " + line for line in text.splitlines())
        text = f"level_{level}:\n  -\n{indented}\nsibling_{level}: {level}\n"
        expected = {f"level_{level}": [expected], f"sibling_{level}": level}
    assert loads(text) == expected
    with pytest.raises(YamlError) as error:
        loads(text + "sibling_0: duplicate\n")
    assert error.value.line == len(text.splitlines()) + 1


def test_large_root_sequence_keeps_records_independent() -> None:
    lines = []
    expected = []
    for index in range(600):
        lines.extend(
            [
                f"- id: record_{index}",
                "  readings:",
                f"    - value: {index}",
                "      accepted: true",
                f"    - value: {-index}",
                "      accepted: false",
                "  tags: []",
                "  extra: {source: sensor}",
            ]
        )
        expected.append(
            {
                "id": f"record_{index}",
                "readings": [
                    {"value": index, "accepted": True},
                    {"value": -index, "accepted": False},
                ],
                "tags": [],
                "extra": UnsupportedYaml("{source: sensor}"),
            }
        )
    result = loads("\n".join(lines))
    assert result == expected
    result[0]["tags"].append("changed")
    assert all(record["tags"] == [] for record in result[1:])
