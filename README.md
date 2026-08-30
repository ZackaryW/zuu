# zuu

## Install
```bash
pip install zuu
```

## Release behavior

Versions use a month-led form such as `202608.29.1`, where the first component
identifies the release month. A push to `main` publishes to PyPI automatically
only when that component changes, such as from `202608` to `202609`. Changes to
the remaining components within the same month do not publish automatically.
The publish workflow can still be run manually for any version.

## Cases

| Case | Utility | Purpose | Depends on | Documentation |
|------|---------|---------|------------|---------------|
| case1 | `UserLevelHasher` | Store and check named hashes for composable filesystem inputs. | `case2` | [Guide](docs/case1/README.md) |
| case2 | `FileSystemSnapshot` | Capture deterministic snapshots of files and directory trees. | — | [Guide](docs/case2/README.md) |
| case3 | `GitIgnorePlan` | Plan, apply, and verify Git-ignore coverage for selected paths. | — | [Guide](docs/case3/README.md) |
| case4 | `MarkdownTable` | Find, extract, compose, and replace Markdown pipe tables. | — | [Guide](docs/case4/README.md) |
| case5 | `ConfinedPath` | Treat paths like addresses inside a fenced property, keeping repository selection and exact target planning portable and confined. | — | [Guide](docs/case5/README.md) |
| case6 | `AffectedTargets` | Choose the smallest declared target set that safely covers changed repository paths. | `case5` | [Guide](docs/case6/README.md) |
| case7 | `ProjectionPlan` | Plan updates to managed outputs without overwriting unowned or locally changed content. | — | [Guide](docs/case7/README.md) |
| case8 | `LayeredMapping` | Stack configuration like transparent sheets, letting later JSON and typed assignments cover earlier defaults without recursive merging. | — | [Guide](docs/case8/README.md) |
| case9 | `TemporaryJsonEnvironment` | Hand structured settings to child processes like a temporary luggage locker, using an environment path as the claim ticket and cleaning up afterward. | — | [Guide](docs/case9/README.md) |
| case10 | `TombstoneOverlay` | Personalize a shared mapping like a correction sheet, overlaying local values and crossed-out keys without changing the original. | — | [Guide](docs/case10/README.md) |
| case11 | `CliSelector` | Choose CLI values like a station clerk honoring tickets already in hand before opening a live terminal checklist. | — | [Guide](docs/case11/README.md) |
