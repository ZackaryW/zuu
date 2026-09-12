## Context

See proposal.md for the reported consumer symptoms. The current `AnsiRenderer` in `src/zuu/case11/terminal.py` renders every label, snapshots only the terminal width at construction, and retains `max(new_height, old_height)` as its frame height. `finish()` clears the old menu but leaves the cursor below those cleared rows. A read-only probe against the consumer's installed ZuU 202609.8.0 produced seven empty rows after a four-agent selector completed at 38 columns. The current repository has the same relevant algorithm.

A 17-choice probe produced 21 physical rows at 38 columns. The user's actual terminal height was not measured, so viewport overflow explains the reported clipping but has not yet been reproduced in their native terminal. Windows cursor-up movement is bounded by the viewport; it cannot reliably recover an origin scrolled offscreen. See [Microsoft's cursor positioning documentation](https://learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#cursor-positioning).

Existing rendering tests check ANSI strings, newline counts, and presence of the summary. They do not verify the cursor immediately after completion or model viewport scrolling. The canonical selection spec also requires dependency-free Windows/POSIX interaction and recoverable terminal modes.

## Goals / Non-Goals

**Goals:** Repair case11 rendering at its existing terminal boundary; make layout and cursor outcomes independently testable; preserve the public selector contract and full-collection state semantics.

**Non-Goals:** New selection controls, search, a general TUI framework, asynchronous redraw while idle, changes to Overspec's prompts or dependency pin, and new runtime dependencies.

## Decisions

### 1. Separate frame layout from terminal painting within case11

Use current width and height to produce a bounded set of physical rows and a visible choice range. Reuse existing display-cell measurement for fitting text. Keep helpers local to the case11 renderer unless implementation demonstrates a separate reusable responsibility; no new utility case is justified by this fix.

Reserve space for the question, compact key help, validation when present, overflow indication, and a safe cursor row. Display a contiguous choice window and shift it only as needed to retain focus. Shorten help and truncate long rows with a visible omission marker when wrapping would consume the choice budget. Expose the highlighted label as fully as the available budget permits. Reject dimensions that cannot support a usable minimum frame through the existing terminal error contract.

Rendering all choices with cursor-up is insufficient because physical rows can exceed the viewport. Adding a third-party widget conflicts with ZuU's standard-library-only contract.

### 2. Keep state independent of visibility

`CheckboxState` continues to own the complete list's focus and selected indexes. Layout consumes that state without filtering the underlying choices. Existing wrap navigation, `a`, `i`, required selection, cancellation, and declaration-order results remain authoritative. A visible subset must never become the selection universe.

### 3. Track active rows separately from rows being erased

Painting must distinguish the new frame extent from the previous extent that requires cleanup. On shrink or finish, clear obsolete owned rows, then return the cursor to immediately below the new content. Initial rendering must accommodate a prompt launched near the bottom of the viewport and establish a recoverable frame origin; reserve room before relying on relative cursor movement. Never clear the whole screen or unrelated scrollback as a cleanup shortcut.

Refresh terminal dimensions on each repaint, including finish. Recalculate the frame before writing it. Width changes can reflow prior terminal output, so merely replacing the cached width is not enough: the repaint strategy must establish that its previous region is still addressable. If a resize makes that impossible with supported terminal capabilities, stop through the recoverable error path without speculative cursor-up erasure. No resize polling or new input event loop is required; the next action triggers adaptation.

### 4. Verify screen outcomes with focused RED/GREEN slices

Extend existing renderer tests with a small test-only terminal screen model at the output boundary. It must account for the ANSI operations used, bounded cursor movement, line clearing, wrapping, and scrolling; first establish those model behaviors so it cannot silently accept invalid cursor movement. Assert visible rows, owned-region cleanup, and final cursor placement rather than snapshots of a preferred escape sequence.

Use three behavior slices: completion and consecutive prompts; a 17-choice constrained viewport with full-list selection; dimension changes and safe failure/restoration. Include cell-width and validation edge cases within these slices. Observe each regression fail for the reported behavior before implementing its fix, then run the relevant existing case11 tests. Do not duplicate the existing key-mapping or public API matrix.

The model cannot establish native console resize/reflow behavior. Record a Windows terminal smoke check with consecutive selectors, navigation through all 17 entries, resize, submit, and cancel; check POSIX interaction when an actual compatible environment is available and clearly report any unavailable platform verification.

## Risks / Trade-offs

- Inline output may reflow differently across terminal hosts after resize → test a real Windows terminal and retain an explicit safe-error path when frame ownership cannot be recovered.
- Compact help or truncated labels can hide detail → preserve question/focus/checked state, indicate omissions, and document constrained-screen behavior.
- A test terminal model can duplicate implementation assumptions → assert terminal semantics independently and supplement it with native smoke evidence.
- Redraw occurs on input → a resized idle menu can remain stale until the next action; this is an intentional boundary for the current synchronous selector.

## Migration Plan

No stored data or public selector API migration is required. Run focused RED/GREEN slices, existing case11 coverage, the repository suite, and native smoke checks before releasing ZuU. A later Overspec change can update its ZuU pin to consume the fix. Rollback consists of reverting the rendering change or retaining the previous consumer pin; no user files or installed skills are changed by this work.
