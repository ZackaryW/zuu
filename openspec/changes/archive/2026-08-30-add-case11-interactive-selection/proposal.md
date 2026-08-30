## Why

Applications can already accept repeated explicit options through CLI frameworks, but
they still need a dependency-free way to fall back to the live checkbox experience
used by ZPP when a person is present. Zuu can extract the small selection lifecycle
and constrained terminal interaction without importing Agent Router, Typer,
Questionary, or Prompt Toolkit.

## What Changes

- Add case11 as a generic CLI choice selector that treats explicit values like a
  completed order and opens an interactive checklist only when no order was supplied.
- Provide a standard-library terminal checklist with wrapping arrow-key navigation,
  space toggling, select-all, inversion, confirmation, and cancellation on supported
  Windows and POSIX terminals.
- Preserve ordered values and distinguish cancellation from an intentionally empty
  selection while enforcing required-selection policy.
- Keep terminal input, rendering, and selection state separated so behavior can be
  tested deterministically without controlling a real console.
- Provide a small `python -m zuu.case11` demonstration that exercises the real
  checklist with illustrative agent choices and repeatable explicit options.
- Document constrained terminal support and explicitly exclude search, async prompts,
  arbitrary styling, descriptions, validation toolbars, and general terminal UI
  framework behavior.

## Capabilities

### New Capabilities

- `terminal-choice-selection`: Resolve explicit or interactively checked generic CLI
  choices through a constrained, dependency-free terminal selection lifecycle.

### Modified Capabilities

None.

## Impact

- Adds `src/zuu/case11/`, `docs/case11/`, and focused `tests/case11/` coverage.
- Updates the generated root case index through case11 metadata.
- Uses only Python 3.12 standard-library facilities, with separate Windows and POSIX
  key-reading paths and ANSI rendering where an interactive terminal is available.
- Does not change existing case APIs or introduce a case dependency.
