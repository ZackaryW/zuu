## ADDED Requirements

### Requirement: Viewport-bounded checklist
The interactive checklist SHALL fit its active frame within the terminal's current width and height, accounting for physical display cells and cursor placement. When all choices cannot fit, it SHALL show a scrolling window containing the highlighted choice and indicate that additional choices exist. Guidance and validation feedback SHALL leave room for at least one visible choice in supported dimensions.

#### Scenario: Navigate a list taller than the terminal
- **WHEN** a checklist with 17 choices is used in a terminal too short to display all choices
- **THEN** the active frame fits the viewport, navigation exposes every choice, and the highlighted choice remains visible without appending duplicate frames

#### Scenario: Preserve selection outside the visible window
- **WHEN** the user selects choices, scrolls them out of view, uses toggle-all or inversion, and submits
- **THEN** operations apply to the full declared collection and results preserve declaration order, regardless of visibility

#### Scenario: Show narrow-screen guidance and validation
- **WHEN** a supported narrow terminal displays long labels or rejects an empty required selection
- **THEN** the layout keeps the highlighted choice and applicable validation feedback visible, with compact guidance and cell-aware text fitting instead of overflowing the viewport

### Requirement: Resize-aware layout
The checklist SHALL refresh available terminal dimensions on each repaint and adapt its layout while preserving focus and checked values. It SHALL avoid repainting outside its owned region. When dimensions or terminal behavior cannot support safe interaction, it SHALL fail clearly and restore the terminal rather than continue with a corrupted display or return a successful selection.

#### Scenario: Resize during navigation
- **WHEN** the terminal becomes narrower or shorter and the user performs the next navigation or selection action
- **THEN** the checklist uses the new dimensions and retains selection state, either repainting safely with the highlighted item visible or reporting an inability to continue safely

#### Scenario: Expand the viewport
- **WHEN** the terminal grows during interaction
- **THEN** the next repaint uses the available space without losing focus or checked values

#### Scenario: Terminal cannot fit a usable checklist
- **WHEN** the viewport cannot accommodate a question, a choice, necessary feedback, and safe cursor placement
- **THEN** selection fails with a clear diagnostic and terminal modes and cursor visibility are restored

### Requirement: Compact completed prompts
On submission or cancellation, the checklist SHALL clear its active choice and feedback rows, retain only its outcome text, and place subsequent output immediately below that text. Outcome text SHALL fit the terminal width; if it occupies multiple physical rows, cursor placement SHALL account for those rows. Cleanup SHALL preserve preceding unrelated output.

#### Scenario: Consecutive selectors
- **WHEN** a four-choice selector completes and a 17-choice selector opens on the same terminal stream
- **THEN** the second question begins immediately below the first outcome without leftover menu-height blank rows or stale choices

#### Scenario: Cancel after validation or scrolling
- **WHEN** a checklist is cancelled after showing a validation error or scrolling through choices
- **THEN** only the cancellation outcome remains from that checklist and the cursor is immediately below it

#### Scenario: Complete near the bottom of the screen
- **WHEN** a checklist starts near the bottom of a terminal containing earlier output and is submitted
- **THEN** completion preserves earlier output, clears owned menu rows, and leaves the next output position directly below the outcome
