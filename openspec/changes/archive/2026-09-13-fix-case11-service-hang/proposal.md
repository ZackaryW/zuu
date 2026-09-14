## Why

Case11 retries exhausted input indefinitely and emits another full frame for every rejected empty submission, allowing a failing input source to hang a caller and captured output to grow. A reported service hang with high RAM use motivates closing these reproduced failure paths; the exact service command and its memory profile were not supplied, and stack overflow has not been observed.

## What Changes

- Report closed input as `TerminalUnavailableError`, including EOF during escape/extended keys and the Windows no-console sentinel, while preserving terminal restoration.
- Keep unsupported non-ASCII input distinct from EOF and preserve ignored-key and escape-timeout behavior.
- Avoid emitting identical consecutive frames, including repeated required-empty submissions and navigation that leaves the screen unchanged.
- Bound temporary layout work by the viewport, choosing compact layout before formatting hidden choices and stopping text fitting once the visible prefix is known.
- Add bounded regression tests, native Windows failure checks, and guidance for unattended callers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `terminal-choice-selection`: Specify closed-input failure and bounded rendering behavior during repeated input and constrained layouts.

## Impact

Changes are confined to case11 readers, rendering, tests, documentation, and its OpenSpec capability. Public signatures and dependencies stay compatible. EOF becomes an error instead of an endless retry. Legitimate interactive sessions still wait for input, and changing frames can still accumulate in a caller-owned output capture.
