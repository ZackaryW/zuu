import pytest

from zuu.case16 import parse_version


@pytest.mark.parametrize("value", [None, 1, "", "latest", "release-1.2", " v1", "v1\n", "1..2", "1-", "1+", "1_beta", "１.２"])
def test_unparseable_versions_return_none(value):
    assert parse_version(value) is None


@pytest.mark.parametrize(("left", "right"), [
    ("v1.9", "v1.10"),
    ("v1", "v1.0.1"),
    ("202609.8.0", "202610.1"),
    ("1.0-alpha", "1.0-alpha.1"),
    ("1.0-alpha.2", "1.0-alpha.10"),
    ("1.0-2", "1.0-alpha"),
    ("1.0-beta", "1.0-rc.1"),
    ("1.0-rc.1", "1.0"),
    ("1.0", "2.0-alpha"),
])
def test_numeric_and_prerelease_ordering(left, right):
    assert parse_version(left) < parse_version(right)


@pytest.mark.parametrize(("left", "right"), [
    ("V1.02.0", "1.2"),
    ("v0.0.0", "0"),
    ("1.0+build.1", "1.0+build.99"),
    ("v1.0-rc.01", "1-rc.1"),
])
def test_equivalent_numeric_cores_prefixes_and_build_metadata(left, right):
    assert parse_version(left) == parse_version(right)
