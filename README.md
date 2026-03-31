# zuu
zack's useful utilities

## Note

This library has gone through several structural changes, which made it harder for other packages to depend on it reliably.

To avoid that going forward, the package now follows a permanent versioned-folder design. If a future change would alter existing behavior, a new feature-version folder will be created instead of changing the previous implementation in place.

The package version format is:

`{yearquarter}.{feature version}.{no breaking change build}`

The package structure is:

```text
zuu/
|- v202601_1/  // starting implementation quarter + feature version
    ...
```

## Setup

Install the development environment with uv:

```bash
uv sync --only-dev
```

## Refresh Current

`src/zuu/current` is a generated thin export layer. It should re-export the newest version folder by resolving the highest folder name matching `v{yearquarter}_{minor}`.

Refresh it with:

```bash
uv run python scripts/update_current.py
```

For example, if both `v202602_1` and `v202603_1` exist, the script points `current` at `v202603_1`. If both `v202602_1` and `v202602_3` exist, it points `current` at `v202602_3`.

