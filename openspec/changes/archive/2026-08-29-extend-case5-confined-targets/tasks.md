## 1. Case5 Public Contract

- [x] 1.1 Add the confined path, target state, immutable plan/evidence, base error,
  and stale-plan error to case5 with an analogy-led `__purpose__`, unchanged
  `__depends__`, and deliberate exports; verify focused public-contract tests confirm
  frozen state and retain all existing imports.
- [x] 1.2 Reuse case5's portable relative-path grammar for the generic confined path
  without changing `RepositoryPath` behavior; verify the existing path matrix and a
  parameterized confined-path valid/invalid matrix both pass.
- [x] 1.3 Place platform-specific traversal and evidence comparison in a named
  case-local module while keeping the primary model in `__init__.py`; verify imports
  use no private API from another case and runtime dependencies remain empty.

## 2. Strict Confined Inspection

- [x] 2.1 Implement trusted-root inspection for absent, regular-file, and directory
  targets; verify each state returns the canonical relative identity and confined
  physical path inside a pytest temporary root without mutation.
- [x] 2.2 Implement allowed-state enforcement; verify unexpected absence, occupied
  creation targets, and file/directory mismatches raise the case5 error family while
  leaving the temporary tree unchanged.
- [x] 2.3 Reject redirected or unsupported descendant entries through lexical
  `lstat` traversal; verify symbolic-link and platform-supported junction scenarios
  never return a target, with explicit skips only when the host cannot create them.
- [x] 2.4 Preserve `RepositoryPath.resolve_file()` and `RepositoryGlob` compatibility;
  verify their existing focused tests pass unchanged alongside the stricter opt-in
  inspection behavior.

## 3. Evidence and Revalidation

- [x] 3.1 Capture immutable evidence for the physical root, existing components,
  observed state, and absent remainder; verify an unchanged file, directory, and
  nested absent target each revalidate to the same plan.
- [x] 3.2 Implement stale-plan comparison without implicit refresh; verify root or
  ancestor replacement, target creation, removal, replacement, kind change, and
  newly occupied absent segments each raise the stale-plan error.
- [x] 3.3 Make the content-integrity boundary observable; verify entry revalidation
  does not claim equality for file bytes or directory descendants and document
  composition with snapshots, hashes, or domain inspectors when needed.

## 4. Documentation and Focused Verification

- [x] 4.1 Expand `docs/case5/README.md` with the fenced-property analogy, target-state
  lifecycle, strict link policy, revalidation evidence, content boundary, errors,
  compatibility behavior, and public examples; verify every example uses only case5
  exports.
- [x] 4.2 Synchronize the existing case5 root index row from its updated metadata and
  verify no case11 or case12 row or package is introduced.
- [x] 4.3 Run `uv run pytest -q tests/case5`, `uv run python scripts/sync_readme.py`,
  and `openspec validate extend-case5-confined-targets --strict`; verify all focused
  behavior and planning artifacts pass without running the repository-wide suite.
