## Context

See `proposal.md` for motivation. Zuu has no runtime dependencies and targets Python
3.12 or later. ZPP currently combines a small explicit-versus-interactive selection
policy with a Questionary checkbox, while Questionary delegates raw input, repainting,
and cleanup to Prompt Toolkit. Case11 must reproduce only the accepted observable
subset without copying either package's architecture.

The behavioral contract is defined in
`specs/terminal-choice-selection/spec.md`. The design must remain useful with values
other than agents and must be testable without requiring a developer's real terminal.

## Goals / Non-Goals

**Goals:**

- Present one cohesive public lifecycle that accepts explicit values first and falls
  back to a live checklist only on an interactive terminal.
- Keep selection transitions deterministic and separate from platform input and ANSI
  output.
- Restore every terminal resource through an exception-safe session boundary.
- Support the specified controls on current Windows consoles and conventional POSIX
  terminals using only the standard library.

**Non-Goals:**

- Reproduce Questionary or Prompt Toolkit as general-purpose terminal frameworks.
- Provide search, scrolling, asynchronous prompts, arbitrary styling, descriptions,
  disabled choices, background-output patching, or custom key maps.
- Parse CLI arguments or translate errors into Typer, Click, or argparse exceptions.
- Guarantee cooperative rendering while unrelated threads write to the same terminal.
- Turn the demonstration module into an application-specific production CLI.

## Decisions

### Use one generic selector as the public lifecycle

Case11 will expose immutable generic choice and result values plus a selector that
owns the message, ordered choices, and required policy. Its selection method accepts
explicit values and returns immediately when they exist; otherwise it evaluates
terminal eligibility and, when allowed, runs the checklist.

The primary API should read like:

```python
selector = CliSelector(
    "Configure agent applications",
    choices=(
        Choice("Codex", Agent.CODEX),
        Choice("Claude Code", Agent.CLAUDE),
    ),
)
selection = selector.select(explicit_agents, required=True)
```

`Choice` values remain application-owned and are compared without requiring a
third-party enum or CLI abstraction. `Selection` carries an ordered tuple and a
separate cancellation flag.

Alternative considered: expose only a low-level `checkbox()` function and leave the
explicit-value policy in every caller. That would fail the requested extraction from
ZPP and repeatedly force callers to coordinate prompt admission and cancellation.

### Keep pure transitions independent of terminal I/O

An internal checkbox state will store the pointed index and selected indexes. It will
consume semantic actions such as up, down, toggle, all, invert, submit, and cancel.
It will not read keys or render strings. This makes wrapping, ordering, required-empty
validation, and cancellation exhaustively testable with ordinary values.

Alternative considered: mutate selection directly inside platform key handlers, as a
small script might. That is shorter initially but makes platform behavior and state
semantics inseparable and difficult to test comprehensively.

### Translate platform input into a small semantic key vocabulary

The Windows backend will use `msvcrt.getwch()` and translate its extended arrow-key
sequences. The POSIX backend will temporarily configure its input file descriptor
with `termios`/`tty` and translate ANSI arrow sequences. Both will emit the same
internal semantic actions.

Platform-only imports will be lazy or guarded so importing case11 works everywhere.
The selector will confirm compatible interactive input and output before entering a
terminal session or emitting a menu.

Alternative considered: parse all input as ANSI bytes. Windows key events exposed by
`msvcrt` use a different representation, so pretending the platforms are identical
would merely hide rather than remove the platform branch.

### Treat terminal changes as a transaction

A session context manager will capture the current input and console modes, enable
the minimum immediate-input and ANSI capabilities, hide the cursor, and restore all
captured state in `finally`. Capability checks occur before the first visible render.
Ctrl+C may arrive as either an input character or `KeyboardInterrupt`; both become a
cancelled result after restoration. Ctrl+Q is handled as an input character.

Alternative considered: let callers recover the terminal after an exception. That
would make a library failure capable of leaving user input or cursor state damaged.

### Repaint complete lines instead of measuring display width

The renderer will own the number of menu lines it emitted. On each state change it
will move to the start of those lines, clear each entire line, and redraw the menu.
Using line clearing avoids horizontal cursor calculations and a dependency on a
Unicode-width library. Choice labels are therefore constrained to printable,
single-line text.

Alternative considered: implement cell-width calculation and partial updates. That
adds a terminal-layout subsystem without improving the fixed checklist experience.

### Keep modules aligned with responsibilities

`case11/__init__.py` may contain the public immutable values, errors, selector policy,
`__purpose__`, `__depends__ = ()`, and `__all__`. Pure checkbox transitions belong in
a named state module; rendering and session orchestration belong in a terminal module;
platform readers belong in small Windows and POSIX modules when separating them makes
guarded imports clearer. This keeps `__init__.py` useful without making it the entire
implementation.

### Provide a minimal module demonstration

`case11/__main__.py` will use standard-library `argparse` to offer the four
illustrative agent choices from the motivating ZPP interaction. Repeated `--agent`
values exercise explicit precedence, `--optional` allows a confirmed empty result,
and omission exercises the actual interactive terminal. Success returns zero,
cancellation returns 130, and selection or terminal errors return 2 with a concise
stderr diagnostic.

Alternative considered: place a Questionary or Typer example executable outside the
case. That would not exercise the dependency-free implementation users need to try,
and it would blur whether case11 itself can supply the experience.

## Risks / Trade-offs

- **Terminal diversity**: escape handling can vary across consoles → keep the public
  terminal contract narrow, reject unsupported sessions before rendering, and cover
  Windows and POSIX adapters independently.
- **Interrupted cleanup**: errors during input or rendering could leave altered modes
  → centralize ownership in one transactional session and test restoration for every
  exit path.
- **Real-terminal tests can be flaky**: CI terminals may not expose a TTY → exhaustively
  test state, key translation, and rendering with fake streams, then keep platform
  smoke tests explicitly gated by actual terminal availability.
- **Concurrent output can corrupt the checklist**: stdlib synchronization would grow
  into a terminal framework → document unrelated concurrent writes as unsupported.
- **Behavioral inspiration could become a disguised port**: Questionary includes far
  broader common controls → implement only the accepted spec from first principles and
  retain no copied Prompt Toolkit abstractions.

## Migration Plan

This is an additive standalone case. Implement case11, synchronize the generated case
index, and let ZPP adopt it later by replacing only its selection-policy and prompt
calls. ZPP's Typer option parsing and Agent definitions remain unchanged. Rolling back
case11 requires removing the new case, tests, guide, and index row before any consumer
declares a dependency.
