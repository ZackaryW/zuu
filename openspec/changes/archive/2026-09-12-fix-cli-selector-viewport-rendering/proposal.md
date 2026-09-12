## Why

ZuU case11 leaves cleared menu rows between consecutive selectors and renders long lists beyond the terminal viewport, causing gaps, clipped choices, and repeated prompts in consumers such as `overspec skill install`. Its existing tests inspect output strings without establishing the resulting visible screen and cursor position, allowing these defects to pass.

## What Changes

- Collapse submitted and cancelled menus to their outcome text and position subsequent output immediately below it.
- Fit the active checklist to the current terminal width and height, using a scrolling choice window that keeps the highlighted item visible and indicates hidden choices.
- Adapt help, long labels, and validation feedback to constrained screens; refresh dimensions on repaint and safely handle terminal resizing.
- Preserve full-list navigation, selection, toggle-all, inversion, cancellation, and explicit-value behavior when only part of the list is visible.
- Add focused regression coverage of visible screen outcomes, including consecutive selectors and a realistic 17-choice menu, with observed RED before implementation and GREEN afterward.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `terminal-choice-selection`: Require viewport-bounded rendering, resize-aware repainting, and clean completion placement for interactive checklists.

## Impact

- Primarily `src/zuu/case11/terminal.py` and its rendering/session integration tests; terminal backends only where the chosen repaint strategy requires support.
- Keep the public `Choice`, `Selection`, and `CliSelector` contract and the standard-library-only runtime dependency policy.
- Update case11 usage documentation to explain scrolling and constrained-terminal behavior.
- Overspec's dependency pin and consumer release are follow-up work outside this ZuU change.
