# Implementation evidence

## Observed RED and GREEN

1. Completion: `uv run pytest tests/case11/test_viewport.py -q` initially produced **2 failed, 1 passed**. Both submission and cancellation left the cursor at row 29 instead of row 22, seven cleared rows below the outcome. After separating active height from cleanup height, `uv run pytest tests/case11/test_viewport.py tests/case11/test_rendering.py -q` produced **11 passed**.
2. Bounded choices: after adding the short/narrow viewport regressions, the viewport file produced **2 failed, 3 passed**. The 17-choice menu scrolled 12 rows into history; the long wide-character label/validation case also overflowed. After adding compact layout and the visible choice window, the viewport and rendering files produced **13 passed**.
3. Resize: the viewport file produced **5 failed, 6 passed** before refresh/recovery was implemented. Expansion retained the old five-choice window; shrink cases did not report an error, including the session restoration path. After the fix, `uv run pytest tests/case11 -q` produced **104 passed**. The unusably-small-screen case was already passing from the compact-layout slice and is not counted as new RED evidence.

The test screen model independently checks bounded cursor movement, wrapping, clearing, wide/combining characters, and scrolling. Behavioral assertions cover the visible rows and cursor position, not just the existence of expected text in a captured output string.

Final edge review extended the unsupported-size case to 1×5 and 38×4. The focused run first produced **1 failed, 2 passed** because the old constructor raised `ValueError` for one column instead of using the recoverable terminal error contract. Removing that inconsistent constructor guard leaves dimension validation at repaint, inside the session lifecycle. Final case11 coverage: **106 passed**.

## Repository suite

- `uv run pytest -q`: collection blocked by five existing duplicate module-name collisions (`test_contract`, `test_lifecycle`, `test_selection`) across case directories.
- `uv run pytest --import-mode=importlib -q`: final run **1,200 passed, 3 skipped**. No repository-wide test configuration changes were made for this renderer fix.

## Native Windows verification

`uv run python tests/case11/windows_smoke.py` passed. The opt-in script opens an isolated hidden native Windows console and uses actual console dimensions, screen-buffer reads, cursor position, console modes, and cursor visibility. It does not resize or change the caller's terminal.

Verified at **38 columns × 10 rows**, expanding to **100 × 30**, then shrinking back:

- Four-agent summary immediately followed by the 17-choice menu.
- Navigation exposes each of the 17 choices and leaves the preceding summary in scrollback.
- Toggle-all submission collapses to the next summary with the cursor immediately below.
- Cancellation after required-selection feedback clears the old menu.
- Expansion reveals all entries while preserving focus and checked state.
- Shrinking raises a restart diagnostic without erasing unknown rows.
- Original console modes and visible cursor are restored.

This is automated native screen verification with scripted state actions, not a claim of manual keyboard or visual testing in the user's PowerShell host. Existing key-reader tests continue to cover keyboard translation. Native POSIX interaction was not exercised in this Windows session; existing POSIX session/reader tests passed within case11 coverage.

## Delivered behavior and boundaries

The renderer refreshes dimensions on input-driven repaint and finish. It safely aborts on any detected shrink because relative cursor movement alone cannot establish ownership after host reflow. Growth is supported. No asynchronous idle redraw, public selector API change, runtime dependency, new reusable utility case, consumer installation, or Overspec dependency pin update is included.
