## 1. Completion and consecutive prompts

- [x] 1.1 Add a minimal test-only terminal screen model for the renderer's output operations; verify bounded cursor movement, wrapping, clearing, and scrolling with independent expected screen states.
- [x] 1.2 RED: reproduce the completion gap with consecutive four-choice and 17-choice selectors, including cancellation and a start near the bottom of the screen; record failing assertions for final cursor placement, stale rows, or preservation of earlier output before changing production code.
- [x] 1.3 GREEN: distinguish active frame height from cleanup extent and reposition after completion; verify the new completion regressions and existing case11 rendering tests pass.

## 2. Bounded choice window

- [x] 2.1 RED: add focused screen-outcome coverage for a 17-choice menu in a narrow, short viewport, long/wide-character labels, and required-selection feedback; verify current rendering fails viewport or focus visibility expectations.
- [x] 2.2 GREEN: implement dimension-aware layout, compact help, overflow indication, and focus-following scrolling; verify the bounded-screen cases pass and full-list toggle-all, inversion, wrap navigation, and submission order still work for hidden choices.

## 3. Resize and recovery

- [x] 3.1 RED: simulate width/height changes between repaints and an unusably small viewport; record failures for stale dimensions or missing safe failure/restoration before implementing adaptation.
- [x] 3.2 GREEN: refresh dimensions on repaint and finish, recover the owned region when safe, and use the existing terminal error path when interaction cannot continue safely; verify focused resize cases, unchanged selections during successful resizing, and mode/cursor restoration after failure.

## 4. Integration and documentation

- [x] 4.1 Run `uv run pytest tests/case11` and `uv run pytest`; record results and the observed RED/GREEN commands for the three behavior slices without treating pre-existing passing tests as RED evidence.
- [x] 4.2 Exercise consecutive selectors, all 17 choices, terminal resizing, submission, and cancellation in a native Windows terminal; record dimensions and screen/cursor outcomes. Run a POSIX smoke check when available and explicitly record any unverified platform behavior.
- [x] 4.3 Update case11 usage documentation with scrolling, compact layout, input-triggered resize refresh, and unsupported-size behavior; verify it matches the implemented behavior and introduces no consumer-specific dependency or API requirement.
