"""Regenerate numbered case rows in the root README."""

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE_NAME = re.compile(r"case([1-9]\d*)")
TABLE_HEADER = "| Case | Utility | Purpose | Depends on | Documentation |"


def read_case(root: Path, package: Path) -> tuple[int, str]:
    """Read one case's literal metadata without importing the package."""
    tree = ast.parse((package / "__init__.py").read_text(encoding="utf-8"))
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                try:
                    values[target.id] = ast.literal_eval(node.value)
                except (TypeError, ValueError):
                    pass

    purpose = values.get("__purpose__")
    depends = values.get("__depends__")
    if not isinstance(purpose, str) or not isinstance(depends, tuple):
        raise ValueError(f"{package.name} needs literal __purpose__ and __depends__")

    exports = values.get("__all__")
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    primary = exports[0] if isinstance(exports, (list, tuple)) and exports else None
    if not isinstance(primary, str):
        primary = classes[-1] if classes else "N/A"

    number = int(CASE_NAME.fullmatch(package.name).group(1))
    dependencies = ", ".join(f"`{name}`" for name in depends) or "—"
    guide = root / "docs" / package.name / "README.md"
    documentation = f"[Guide](docs/{package.name}/README.md)" if guide.is_file() else "—"
    utility = f"`{primary}`" if primary != "N/A" else primary
    row = (
        f"| {package.name} | {utility} | {purpose} | "
        f"{dependencies} | {documentation} |"
    )
    return number, row


def discover_rows(root: Path) -> list[str]:
    """Render all numbered cases except case0 in numeric order."""
    package_root = root / "src" / "zuu"
    cases = [
        read_case(root, path)
        for path in package_root.iterdir()
        if path.is_dir() and CASE_NAME.fullmatch(path.name)
    ]
    return [row for _, row in sorted(cases)]


def synchronize(root: Path = ROOT) -> bool:
    """Update dynamic table rows while keeping the case0 row unchanged."""
    readme = root / "README.md"
    lines = readme.read_text(encoding="utf-8").splitlines()
    first_row = lines.index(TABLE_HEADER) + 2
    table_end = first_row
    while table_end < len(lines) and lines[table_end].startswith("|"):
        table_end += 1

    case0 = next(row for row in lines[first_row:table_end] if row.startswith("| case0 "))
    updated = [*lines[:first_row], case0, *discover_rows(root), *lines[table_end:]]
    content = "\n".join(updated) + "\n"
    changed = content != readme.read_text(encoding="utf-8")
    if changed:
        readme.write_text(content, encoding="utf-8", newline="\n")
    return changed


if __name__ == "__main__":
    print("README case index updated" if synchronize() else "README case index current")
