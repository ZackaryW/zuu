"""Regenerate numbered case rows in the root README."""

import ast
import re
from pathlib import Path
from types import SimpleNamespace

from zuu.case4 import Column, MarkdownTable


ROOT = Path(__file__).resolve().parents[1]
CASE_NAME = re.compile(r"case([1-9]\d*)")


def _literal(tree: ast.Module, name: str, default: object = None) -> object:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    return default


def _read_case(root: Path, package: Path) -> SimpleNamespace:
    tree = ast.parse((package / "__init__.py").read_text(encoding="utf-8"))
    purpose = _literal(tree, "__purpose__")
    depends = _literal(tree, "__depends__")
    exports = _literal(tree, "__all__", ())
    if not isinstance(purpose, str) or not isinstance(depends, tuple):
        raise ValueError(f"{package.name} needs literal __purpose__ and __depends__")

    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    primary = exports[0] if isinstance(exports, (list, tuple)) and exports else None
    guide = root / "docs" / package.name / "README.md"
    return SimpleNamespace(
        name=package.name,
        purpose=purpose,
        depends=depends,
        primary=primary if isinstance(primary, str) else classes[-1] if classes else "N/A",
        documented=guide.is_file(),
    )


COLUMNS = (
    Column("Case", lambda case: case.name),
    Column("Utility", lambda case: f"`{case.primary}`" if case.primary != "N/A" else "N/A"),
    Column("Purpose", lambda case: case.purpose),
    Column("Depends on", lambda case: ", ".join(f"`{name}`" for name in case.depends) or "—"),
    Column(
        "Documentation",
        lambda case: f"[Guide](docs/{case.name}/README.md)" if case.documented else "—",
    ),
)


def compose_case_table(root: Path) -> MarkdownTable:
    packages = (
        path
        for path in (root / "src" / "zuu").iterdir()
        if path.is_dir() and CASE_NAME.fullmatch(path.name)
    )
    sources = (
        _read_case(root, path)
        for path in sorted(packages, key=lambda path: int(path.name[4:]))
    )
    return MarkdownTable.compose(COLUMNS, sources)


def synchronize(root: Path = ROOT) -> bool:
    readme = root / "README.md"
    document = readme.read_text(encoding="utf-8")
    generated = compose_case_table(root)
    current = MarkdownTable.find(document, generated.headings)
    updated = current.replace_in(
        document,
        generated,
        exclude=lambda row: row["Case"] == "case0",
    )
    if updated == document:
        return False
    readme.write_text(updated, encoding="utf-8", newline="\n")
    return True


if __name__ == "__main__":
    print("README case index updated" if synchronize() else "README case index current")
