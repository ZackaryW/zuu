## Context

See proposal.md for the incident and scope. `run_checkbox` retries `None` immediately. Both readers currently translate an empty character to `None`; POSIX also decodes unsupported bytes to the same empty string. The renderer constructs all logical and wrapped rows before choosing compact layout, and writes unchanged frames repeatedly.

Bounded probes reproduced 100,000 empty reads with constant stack depth. Repeated rejected submissions retained approximately 1.8 MB for 5,000 actions in `StringIO`, while discarding output kept memory low. A detached Windows subprocess explicitly calling `FreeConsole()` returned `\uffff` from `msvcrt.getwch()`. This is evidence for a console-loss guard, not proof of the original incident. CPython directly returns the CRT character in [msvcrt_getwch_impl](https://github.com/python/cpython/blob/main/PC/msvcrtmodule.c); the local native probe establishes the sentinel behavior used here.

## Goals / Non-Goals

**Goals:** Fail at the input boundary on terminal exhaustion, retain the existing cleanup transaction, prevent duplicate-frame output growth, and keep constrained layout work proportional to visible content rather than the total choice collection.

**Non-Goals:** Idle timeouts, limits on legitimate user actions, global output-capture quotas, a new terminal backend, arbitrary infinite choice iterables, or changing generic choice equality/selection semantics. No release, consumer dependency update, or service deployment is implied.

## Decisions

1. **Readers raise `TerminalUnavailableError` for exhaustion.** Check empty characters at every consumed key position, plus `\uffff` on Windows. Decode POSIX bytes with replacement so unsupported bytes remain distinguishable from zero-byte EOF. Preserve continuation readiness timeouts. Returning cancellation would hide terminal failure; retry sleeps would only slow a permanent hang. Existing context managers already restore modes and cursor visibility on exceptions.

2. **Suppress identical painted frames at the renderer boundary.** Retain only the last successful visible frame and compare before writing. Dimension validation still runs first, and cache updates follow successful output. This covers repeated required-empty submits, single-choice navigation, and offscreen changes without copying the entire selected set or retaining frame history. Changed frames, finish cleanup, and supported expansion continue to paint normally.

3. **Bound candidate layout before allocating it.** A collection whose minimum row count cannot fit goes directly to compact layout. For shorter collections, inspect bounded label prefixes and cap the candidate question to the viewport's display-cell budget before formatting and wrapping. A truncated candidate necessarily overflows and selects compact layout. Fit compact text in one pass, stopping after enough display cells establish truncation. Preserve combining/wide-character treatment and exact-fit text. This avoids full-collection row lists and full long-text wrapping. Declared strings and the selection set remain application-sized; combining sequences can require additional characters for the same visible width.

4. **Use bounded behavioral regressions.** Reader tests fail after an extra unexpected read rather than entering an unbounded loop. Exercise real pipe EOF with a closed writer and Windows console loss in a time-limited subprocess, plus normal cleanup through injected platform sessions. Stress repeated input using output length, and constrain layout work with counted character visits on large but finite strings. These assertions detect unbounded work without depending on wall-clock speed or risking another OOM.

## Risks / Trade-offs

- [Console failure conventions vary] -> Cover empty injected reads and the locally observed Windows sentinel; propagate other read failures through existing cleanup.
- [Frame caching could hide resize errors] -> Refresh dimensions before equality checks and test unchanged actions during shrink/growth.
- [Prefix fitting could alter Unicode boundaries] -> Preserve exact-fit, wide and combining character behavior with focused tests and existing screen checks.
- [A caller can capture arbitrarily many changing frames] -> Document caller responsibility for bounded captures and explicit input in automation; do not impose surprising interaction deadlines.
- [The original service trigger is unknown] -> Record reproduced defects and verification limits without asserting that its full memory incident was reproduced.

## Migration Plan

Run focused regressions through RED/GREEN, then the full repository suite, native Windows smoke checks, and strict OpenSpec validation. Update the guide, synchronize the added requirements, and archive the completed change. No data migration is required; rollback is a source revert.
