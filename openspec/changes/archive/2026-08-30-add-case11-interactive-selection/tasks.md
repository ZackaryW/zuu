## 1. Public Selection Contract

- [x] 1.1 Create case11 metadata, documented public errors, immutable generic
  `Choice` and `Selection` values, and the `CliSelector` public surface; verify
  `tests/case11/test_contract.py` covers valid construction, unsafe labels, duplicate
  values, frozen results, `__all__`, `__purpose__`, and `__depends__ = ()`.
- [x] 1.2 Implement explicit-value precedence, first-seen deduplication, unknown-value
  rejection, and required/optional noninteractive outcomes; verify focused policy
  tests prove explicit values never inspect, read, or repaint a terminal.
- [x] 1.3 Implement the pure checkbox transition model for wrapping movement, Space,
  `a`, `i`, Enter, Ctrl+C, and Ctrl+Q; verify an in-memory transition matrix covers
  every action, declaration-order results, required empty submission, and distinct
  cancellation without a real console.

## 2. Terminal Interaction

- [x] 2.1 Implement the whole-line ANSI checklist renderer with highlighted and
  checked indicators, instruction and validation text, cursor hiding/restoration,
  and bounded repainting; verify exact-output tests with fake streams show that each
  update replaces the active menu instead of appending another complete copy.
- [x] 2.2 Implement semantic key translation for Windows `msvcrt` extended keys and
  POSIX ANSI sequences behind guarded platform adapters; verify deterministic reader
  tests cover arrows, Space, `a`, `i`, Enter, Ctrl+C, Ctrl+Q, incomplete sequences,
  and ignored keys without depending on the host platform.
- [x] 2.3 Implement transactional Windows console and POSIX terminal sessions that
  probe capability before rendering and restore captured modes in `finally`; verify
  fake-platform tests cover normal submission, cancellation, input failure, render
  failure, setup failure, and restoration failure precedence, with only optional
  platform smoke tests gated by real TTY availability.

## 3. Composed Selector Lifecycle

- [x] 3.1 Connect the selector policy, terminal session, renderer, reader, and pure
  state through replaceable internal boundaries; verify end-to-end fake-terminal
  tests reproduce the ZPP-style multi-agent interaction and return generic values
  without importing Agent Router, Typer, Questionary, or Prompt Toolkit.
- [x] 3.2 Exercise required and optional interactive flows through complete scripted
  key sequences; verify prompt admission, select-all clearing, inversion, submission,
  cancellation, validation feedback, terminal cleanup, and no filesystem or process
  mutation beyond the supplied streams.

## 4. Documentation and Verification

- [x] 4.1 Add `docs/case11/README.md` using the station-clerk and checklist analogy;
  verify public examples cover explicit Typer values, interactive fallback, generic
  non-agent values, cancellation, required selection, supported controls, platform
  expectations, and all declared non-goals using only case11's public API.
- [x] 4.2 Synchronize the root case index from case11 metadata and verify case11 lists
  `CliSelector` as its first `__all__` export with no case dependencies.
- [x] 4.3 Add a standard-library `case11/__main__.py` demonstration with repeatable
  `--agent` values, `--optional`, selected-value output, and distinct success,
  cancellation, and error statuses; verify `tests/case11/test_main.py` covers explicit
  precedence, interactive delegation, empty results, cancellation, and failures, and
  document the runnable commands in the case11 guide.
- [x] 4.4 Run only `uv run pytest -q tests/case11`,
  `uv run python scripts/sync_readme.py`, and
  `openspec validate add-case11-interactive-selection --strict`; verify the focused
  suite, generated index, and complete OpenSpec change all pass.
