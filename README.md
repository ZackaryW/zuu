# zuu

## Cases

| Case | Utility | Purpose | Depends on | Documentation |
|------|---------|---------|------------|---------------|
| case1 | `UserLevelHasher` | Store and check named hashes for composable filesystem inputs. | `case2` | [Guide](docs/case1/README.md) |
| case2 | `FileSystemSnapshot` | Capture deterministic snapshots of files and directory trees. | — | [Guide](docs/case2/README.md) |
| case3 | `GitIgnorePlan` | Plan, apply, and verify Git-ignore coverage for selected paths. | — | [Guide](docs/case3/README.md) |
| case4 | `MarkdownTable` | Find, extract, compose, and replace Markdown pipe tables. | — | [Guide](docs/case4/README.md) |
| case5 | `RepositoryPath` | Make repository-relative path selection safe and predictable across platforms. | — | [Guide](docs/case5/README.md) |
| case6 | `AffectedTargets` | Choose the smallest declared target set that safely covers changed repository paths. | `case5` | [Guide](docs/case6/README.md) |
| case7 | `ProjectionPlan` | Plan updates to managed outputs without overwriting unowned or locally changed content. | — | [Guide](docs/case7/README.md) |
