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

Install Lefthook for local git hooks:

```bash
uv tool install lefthook
lefthook install
```

## Refresh Current

`src/zuu/current` is a generated thin export layer. It should re-export the newest version folder by resolving the highest folder name matching `v{yearquarter}_{minor}`.

Refresh it with:

```bash
uv run python scripts/update_current.py
```

Check whether it is already up to date without modifying files:

```bash
uv run python scripts/update_current.py --check
```

The pre-commit hook uses an automatic mode instead. If `src/zuu/current` is stale,
the hook regenerates it and stages the updated files automatically.

For example, if both `v202602_1` and `v202603_1` exist, the script points `current` at `v202603_1`. If both `v202602_1` and `v202602_3` exist, it points `current` at `v202602_3`.

## Bump Micro Version

When a change stays within the existing newest version folder and does not introduce a new `v{yearquarter}_{minor}` folder under `src/zuu`, bump the third segment of the package version with:

```bash
uv run python scripts/bump_micro_version.py
```

This script only updates `pyproject.toml` when the current package version already matches the newest versioned source folder. If a newer version folder exists, it fails instead of guessing the next feature version.

To verify that staged changes under the newest version folder include the required micro version bump without modifying files:

```bash
uv run python scripts/bump_micro_version.py --check
```

The pre-commit hook uses an automatic mode instead. If the newest version folder changed and the staged package version has not been bumped yet, the hook increments `pyproject.toml` and stages that file for the commit.

## Hooks

The repo includes [lefthook.yml](d:/zuu/lefthook.yml) with `pre-commit` automation for both generated `src/zuu/current` exports and micro version bumps. If a commit still fails, it means the hook could not safely fix the problem automatically and you should run `uv run python scripts/update_current.py` or `uv run python scripts/bump_micro_version.py`, review the resulting changes, and commit again.

