# case11: Explicit or interactive CLI selection

## Provenance and compatibility target

**Source baseline inspected on 2026-08-30:**

- ZPP `2.2.2`: explicit-versus-interactive agent selection policy from
  `zpp.utils.agent_selection` and the prompt adapter in `zpp.cli.shared`;
- Questionary `2.1.1`: the observable checkbox controls and selection experience;
- Prompt Toolkit `3.0.53`: the terminal engine used underneath Questionary, studied
  to identify the platform and cleanup responsibilities that case11 had to replace.

ZPP's surrounding environment also used Typer `0.27.1` and Agent Router `0.1.3`.
Case11 does not reimplement their argument parsing or agent model: CLI frameworks keep
parsing repeated options, and callers keep ownership of their values.

This is a standard-library reimplementation of that narrow behavior, not vendored or
copy-pasted package code. Its goal is a similar-enough experience for small utilities:
explicit values win, an interactive checkbox appears when appropriate, and terminal
state is restored afterward—without making applications depend on the larger ZPP,
Questionary, or Prompt Toolkit stacks. Compatibility is behavioral and deliberately
limited to the controls and lifecycle documented below; it is not API compatibility
with Questionary or a replacement for Prompt Toolkit.

`case11` works like a station clerk. If a traveler already hands over named tickets,
the clerk honors those tickets immediately. If no tickets were supplied and a person
is standing at the counter, the clerk opens a live checklist. Automation never gets
stuck waiting for a person who is not there.

This combines two responsibilities into one lifecycle:

- CLI frameworks may parse explicit repeated options;
- `CliSelector` validates those values or falls back to a dependency-free terminal
  checklist when interactive input and output are available.

## Dependencies

This case is standalone and uses only the Python 3.12 standard library. It does not
depend on Typer, Click, Agent Router, Questionary, Prompt Toolkit, or another zuu case.

## Define a selector

Each `Choice` pairs a printable single-line label with an application-owned value:

```python
from enum import StrEnum

from zuu.case11 import Choice, CliSelector


class Agent(StrEnum):
    CODEX = "codex"
    CLAUDE = "claude"
    PI = "pi"
    KIMI = "kimi"


selector = CliSelector(
    "Configure agent applications",
    choices=(
        Choice("Codex", Agent.CODEX),
        Choice("Claude Code", Agent.CLAUDE),
        Choice("Pi", Agent.PI),
        Choice("Kimi", Agent.KIMI),
    ),
)
```

Labels must be non-empty printable single lines, values must be unique, and at least
one choice is required. Values need only support ordinary equality; mutable values
such as lists and dictionaries are allowed.

## Use explicit Typer options first

Typer owns repeated option parsing. Case11 owns what happens after parsing:

```python
from typing import Annotated

import typer

from zuu.case11 import Choice, CliSelector


app = typer.Typer()

selector = CliSelector(
    "Configure agent applications",
    choices=(
        Choice("Codex", "codex"),
        Choice("Claude Code", "claude"),
        Choice("Pi", "pi"),
        Choice("Kimi", "kimi"),
    ),
)


@app.command()
def configure(
    agent: Annotated[list[str] | None, typer.Option("--agent")] = None,
) -> None:
    selection = selector.select(tuple(agent or ()), required=True)
    if selection.cancelled:
        raise typer.Abort()
    typer.echo(f"Selected: {', '.join(selection.values)}")
```

Given explicit values, no terminal is inspected, read, or repainted:

```text
configure --agent codex --agent pi
```

Repeated explicit values are deduplicated in first-seen order. An explicit value not
declared by the selector raises `SelectionError`.

## Fall back to the live checklist

With no explicit values in an interactive terminal, the same call opens:

```text
? Configure agent applications (Use arrow keys to move, <space> to select, <a> to toggle, <i> to invert)
» ○ Codex
  ○ Claude Code
  ○ Pi
  ○ Kimi
```

The controls are:

- Up and Down move the pointer and wrap at either end;
- Space checks or unchecks the pointed choice;
- `a` checks everything when anything is unchecked, or clears everything otherwise;
- `i` inverts every checked state;
- Enter confirms;
- Ctrl+C and Ctrl+Q cancel.

Checked results are returned in declared choice order, regardless of the order in
which they were toggled. The active menu is repainted in place and collapses to a
one-line outcome after confirmation or cancellation.

## Try the real terminal experience

Case11 includes a small standard-library demonstration with the motivating agent
choices:

```powershell
uv run python -m zuu.case11
```

It opens the actual live checklist when run from an interactive terminal. You can
also exercise explicit precedence without prompting:

```powershell
uv run python -m zuu.case11 --agent codex --agent pi
```

Use `--optional` to permit an empty confirmation or noninteractive omission:

```powershell
uv run python -m zuu.case11 --optional
```

The demonstration exits with status `0` after success, `130` after cancellation, and
`2` for selection or terminal errors. It exists to exercise case11 directly; it is
not an agent-management application.

## Required, empty, and cancelled results

`required=True` means a person cannot confirm an empty checklist. The menu remains
active and displays a validation message until a choice is checked or the user
cancels.

Cancellation is not an empty answer:

```python
selection = selector.select(required=True)

if selection.cancelled:
    print("The traveler left the counter.")
else:
    print(selection.values)
```

- `Selection((), cancelled=False)` means an optional empty choice was confirmed or
  optional automation supplied nothing.
- `Selection((), cancelled=True)` means interactive selection was cancelled.

When input or output is not interactive, the selector never prompts. Optional
selection returns an empty non-cancelled result; required selection raises
`SelectionError` and tells the caller to provide explicit values.

## Generic values

The selector has no knowledge of agents. It can choose output formats, deployment
regions, plugins, profiles, or other application values:

```python
format_selector = CliSelector(
    "Choose export formats",
    choices=(
        Choice("JSON", {"extension": ".json"}),
        Choice("CSV", {"extension": ".csv"}),
    ),
)

selection = format_selector.select(required=False)
```

## Terminal support and recovery

On Windows, case11 reads immediate console keys with `msvcrt` and enables ANSI
processing through `ctypes`. On POSIX systems it uses `termios`, `tty`, `os.read`, and
short readiness checks for arrow-key sequences.

Before drawing, both input and output must be terminals and the required platform
capabilities must be available. Unsupported sessions raise `TerminalUnavailableError`
before presenting a partial checklist.

Input modes and cursor visibility are restored after confirmation, cancellation,
input failure, rendering failure, or another exception. Case11 cannot coordinate
unrelated threads that print into the same terminal while the checklist is active.

`select()` accepts `input_stream` and `output_stream` keyword arguments and otherwise
uses `sys.stdin` and `sys.stdout`. Explicit selections do not inspect these streams.
Interactive replacements must expose truthful `isatty()` behavior and the platform
console or file-descriptor operations required by the session.

## Errors

- `SelectionError` reports invalid messages or choices, duplicate values, unknown
  explicit values, and missing required noninteractive input.
- `TerminalUnavailableError` is a `SelectionError` for unsupported console handles,
  terminal modes, platforms, or restoration failures.

`Choice`, `Selection`, and `CliSelector` are immutable. A cancelled `Selection`
cannot be constructed with selected values.

## Deliberate limits

Case11 is a checklist, not a terminal UI framework. It does not provide search,
scrolling, asynchronous prompts, disabled choices, descriptions, arbitrary styling,
validation toolbars, custom key maps, or background-output patching.

## Tests

Run only the focused case11 suite:

```powershell
uv run pytest -q tests/case11
```
