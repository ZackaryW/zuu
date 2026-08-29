from pathlib import Path
from runpy import run_path

import pytest


SCRIPT = run_path(str(Path(__file__).parents[2] / "scripts" / "sync_readme.py"))
discover_rows = SCRIPT["discover_rows"]
synchronize = SCRIPT["synchronize"]


README = """# zuu

| Case | Utility | Purpose | Depends on | Documentation |
|------|---------|---------|------------|---------------|
| case0 | `manual` | Kept manually. | — | — |
| case9 | `Stale` | Replaced. | — | — |
"""


def add_case(root: Path, number: int, body: str, *, documented: bool = False) -> None:
    package = root / "src" / "zuu" / f"case{number}"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(body, encoding="utf-8")
    if documented:
        guide = root / "docs" / f"case{number}"
        guide.mkdir(parents=True)
        (guide / "README.md").write_text("# Guide\n", encoding="utf-8")


def test_synchronize_uses_first_export_and_numeric_order(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(README, encoding="utf-8")
    add_case(
        tmp_path,
        10,
        '__purpose__ = "Tenth."\n__depends__ = ("case2",)\n'
        '__all__ = ["Primary", "Other"]\n',
        documented=True,
    )
    add_case(
        tmp_path,
        2,
        '__purpose__ = "Second."\n__depends__ = ()\n__all__ = ["Second"]\n',
    )

    assert synchronize(tmp_path) is True

    result = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "| case0 | `manual` | Kept manually. | — | — |" in result
    assert "| case2 | `Second` | Second. | — | — |" in result
    assert "| case10 | `Primary` | Tenth. | `case2` | [Guide]" in result
    assert result.index("| case2 |") < result.index("| case10 |")
    assert "case9" not in result


@pytest.mark.parametrize(
    ("body", "primary"),
    [
        (
            '__purpose__ = "Fallback."\n__depends__ = ()\n'
            "class First: pass\nclass Last: pass\n",
            "Last",
        ),
        ('__purpose__ = "Fallback."\n__depends__ = ()\n', "N/A"),
    ],
)
def test_missing_exports_fall_back_to_last_class(
    tmp_path: Path,
    body: str,
    primary: str,
) -> None:
    add_case(tmp_path, 1, body)

    assert f"| case1 | {'`' if primary != 'N/A' else ''}{primary}" in discover_rows(tmp_path)[0]
