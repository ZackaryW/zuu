from zuu.case1 import UserLevelHasher


class EncryptedMemoryReference:
    def __init__(self):
        self.encrypted: bytes | None = None

    def read(self) -> bytes | None:
        if self.encrypted is None:
            return None
        return bytes(byte ^ 0xA5 for byte in self.encrypted)

    def write(self, data: bytes) -> None:
        self.encrypted = bytes(byte ^ 0xA5 for byte in data)


def test_reference_and_hash_strategy_are_composable(tmp_path):
    governed = tmp_path / "input.txt"
    governed.write_text("data", encoding="utf-8")
    reference = EncryptedMemoryReference()

    def names_only(snapshot):
        return "|".join(entry.relative_path for entry in snapshot.entries)

    hasher = UserLevelHasher(
        tmp_path,
        reference=reference,
        hashers={"names-only": names_only},
    )
    hasher.register("inputs", [governed], hasher="names-only")

    assert reference.encrypted is not None
    assert b'"version"' not in reference.encrypted
    assert hasher.match("inputs", lambda: True, lambda: False) is True
