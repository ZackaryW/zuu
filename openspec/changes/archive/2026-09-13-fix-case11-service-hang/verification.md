# Verification: fix-case11-service-hang

## Assessment

| Dimension | Result |
| --- | --- |
| Completeness | All 6 implementation tasks delivered; both requirements implemented |
| Correctness | All 6 delta scenarios covered; full suite and native Windows checks passed |
| Coherence | Reader guards, successful-frame cache, and bounded candidate layout follow the design |

No critical issues, warnings, or actionable design deviations were found. No verification dimension was skipped. The original service incident and native POSIX terminal operation were not reproduced; those evidence limits are detailed below.

## Observed RED and GREEN

1. `uv run pytest tests/case11/test_readers.py tests/case11/test_sessions.py -q --tb=short` initially produced **15 failed, 34 passed**. Failures included missing EOF errors and lifecycle probes failing on the first unexpected retry. The native Windows console-loss regression separately failed with `lost console was ignored`. After reader guards and distinct unsupported-byte decoding, the reader/session run produced **50 passed**.
2. `uv run pytest tests/case11/test_rendering_resources.py tests/case11/test_terminal_lifecycle.py -q --tb=short` initially produced **6 failed, 17 passed**. Repeated empty submissions captured 1,110,460 characters versus 682 for one submission before a successful selection; cancellation had the same growth pattern. Large-list and long-text probes exceeded a 5,000-character measurement budget and stopped safely.
3. After renderer changes, `uv run pytest tests/case11 -q --tb=short` produced **135 passed**. Verification then expanded the existing escape-timeout regression to cover both continuation positions and a subsequent valid key.
4. Final `uv run pytest --import-mode=importlib -q -o faulthandler_timeout=30`: **1,230 passed, 3 skipped**, including the final 136 case11 cases. Importlib mode follows the existing repository suite convention for repeated test module names.
5. `uv run python tests/case11/windows_smoke.py`: **passed** in an isolated hidden native console. Checked consecutive prompts, 17 choices, submit/cancel, expansion, safe shrink, and restored modes/cursor.
6. `openspec validate fix-case11-service-hang --strict`: **passed**. `git diff --check`: **passed**.
7. Main-spec synchronization comparison confirmed both added requirements match the delta exactly, each appears once, and all pre-existing content is preserved. `openspec validate --specs --strict`: **2 passed, 0 failed**.

## Requirement and scenario evidence

| Scenario | Implementation | Verification |
| --- | --- | --- |
| Input closes while waiting | `posix.py:72`, `windows.py:50` raise the existing terminal error | Empty-reader, real closed-pipe, native detached Windows console, and session cleanup tests |
| Input closes during a multi-character key | Every first/continuation read uses the guarded boundary | POSIX EOF at both continuation positions; Windows empty/sentinel cases with both extended prefixes; lifecycle tests reject any retry |
| Unsupported bytes and escape timeout | POSIX replacement decoding and existing readiness boundary | UTF-8 bytes ignored before Space and EOF; both escape timeouts followed by a valid Space |
| Repeated empty submissions | `terminal.py:142` retains only the last successful visible frame | 5,000 rejected submissions emit exactly the same output as one, then successfully submit or cancel |
| Unchanged navigation and resize | `terminal.py:50` checks dimensions before frame equality | Single-choice navigation emits nothing; expansion updates layout; shrink fails without writing |
| Large collection in small viewport | Early compact choice, bounded question prefix, one-pass fitting | 10,000 choices and million-character label/question probes stay within the measurement/output budgets and preserve focused selection; existing viewport/full-list and Unicode tests pass |

Paths above are relative to `src/zuu/case11/`. Regression files are `tests/case11/test_readers.py`, `test_sessions.py`, `test_terminal_lifecycle.py`, and `test_rendering_resources.py`; existing `test_viewport.py` and `test_rendering.py` cover screen outcomes.

## Bounded memory probes

With a two-choice required selector and `StringIO`, one rejected submission followed by cancellation captured **346 characters**; 5,000 rejected submissions followed by cancellation also captured **346 characters**. Traced peak allocations during those runs were 4,312 and 4,626 bytes respectively. This measures the selector call after setup, not whole-process RAM.

For a 38-by-10 viewport, additional traced allocations during a single render peaked at:

| Input, allocated before tracing | Peak render allocation | Captured characters |
| --- | ---: | ---: |
| 10,000 short choices, focus on last | 2,201 bytes | 174 |
| One million-character label | 1,654 bytes | 101 |
| One million-character question | 4,600 bytes | 100 |

These measurements are diagnostic evidence, not portable byte-exact test thresholds. Durable regressions bound character visits and captured output instead.

## Limits

- The original service command, input stream, and process memory profile were not supplied. This change fixes reproduced failure paths and does not claim to explain every part of the reported 70% RAM incident.
- The exhausted-input probe showed constant stack depth; no stack overflow was observed.
- Real POSIX pipe reads were tested on Windows; POSIX mode restoration was tested through injected platform APIs. A native POSIX TTY was not exercised.
- An open terminal still waits for a person. Legitimate changing frames can grow an unbounded caller-owned capture. The guide now explains explicit/noninteractive input and bounded interactive test harnesses.
- Declared choice data and selection sets remain proportional to application input. Long runs of combining characters can require more code points than their visible cell count; no new text-content limit is imposed.
