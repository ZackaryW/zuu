from pathlib import Path

import pytest

from zuu.case1 import RegistryFormatError, UserLevelHasher


class StoredReference:
    def __init__(self, payload: object):
        self.payload = payload

    def read(self) -> object:
        return self.payload

    def write(self, data: bytes) -> None:
        self.payload = data


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"[]",
        b'{"version":2,"entries":{}}',
        b'{"version":1,"entries":[]}',
        b'{"version":1,"entries":{"build":{"paths":"input.txt"}}}',
        "not bytes",
    ],
)
def test_registry_rejects_malformed_or_unsupported_storage(
    tmp_path: Path,
    payload: object,
) -> None:
    hasher = UserLevelHasher(tmp_path, reference=StoredReference(payload))  # type: ignore[arg-type]

    with pytest.raises(RegistryFormatError):
        hasher.match("build", lambda: None, lambda: None)


def test_registry_persists_across_hasher_instances(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("first", encoding="utf-8")
    UserLevelHasher(tmp_path).register("build", ["input.txt"])

    restored = UserLevelHasher(tmp_path)

    assert restored.match("build", lambda: "same", lambda: "changed") == "same"
