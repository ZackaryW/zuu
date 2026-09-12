# terminal-choice-selection Specification

## Purpose

Choose CLI values like a station clerk honoring tickets already in hand before
opening a live checklist, while preserving cancellation and restoring the terminal
after use.

## Requirements

### Requirement: Ordered generic choices
The capability SHALL accept an ordered, non-empty collection of choices whose
display labels are non-empty, single-line, and printable and whose values are unique.
Choice values SHALL remain generic application-owned values rather than values from a
particular CLI framework or agent package.

#### Scenario: Preserve declared choice order
- **WHEN** a caller declares several valid labeled choices
- **THEN** the capability preserves their declaration order for display and results

#### Scenario: Reject ambiguous choices
- **WHEN** choices are empty, have an empty or unsafe display label, or repeat a value
- **THEN** the capability rejects the declaration before opening a terminal session

### Requirement: Explicit selection precedence
Explicit values supplied by a caller SHALL take precedence over interactive
selection. They SHALL be validated against the declared choices, deduplicated in
first-seen order, and returned without reading from or repainting a terminal.

#### Scenario: Use repeated CLI values without prompting
- **WHEN** a caller supplies valid explicit values containing a duplicate
- **THEN** the capability returns each selected value once in first-seen order and does not prompt

#### Scenario: Reject an unknown explicit value
- **WHEN** an explicit value is not among the declared choices
- **THEN** the capability rejects the selection without opening a terminal session

### Requirement: Interactive fallback policy
When no explicit values are supplied, the capability SHALL open the checklist only
when its input and output support interactive terminal use. Without an interactive
terminal it SHALL return an empty selection when optional and fail when a selection
is required.

#### Scenario: Prompt a person when no explicit values exist
- **WHEN** no explicit values are supplied and interactive input and output are available
- **THEN** the capability opens the live checklist

#### Scenario: Leave optional automation noninteractive
- **WHEN** no explicit values are supplied, no interactive terminal is available, and selection is optional
- **THEN** the capability returns an empty non-cancelled selection without reading input

#### Scenario: Reject missing required automation input
- **WHEN** no explicit values are supplied, no interactive terminal is available, and selection is required
- **THEN** the capability reports that explicit values are required

### Requirement: Live checkbox controls
The interactive checklist SHALL start on the first choice, show the highlighted and
checked states, wrap upward and downward navigation, toggle the highlighted choice
with Space, toggle all choices with `a`, invert all choices with `i`, and submit with
Enter.

#### Scenario: Navigate and toggle choices
- **WHEN** the user moves beyond either end of the list and toggles the highlighted choice
- **THEN** focus wraps to the opposite end and the chosen value changes checked state

#### Scenario: Toggle all choices
- **WHEN** the user presses `a` while any choice is unchecked and then presses `a` again
- **THEN** the first action checks every choice and the second clears every choice

#### Scenario: Invert choices
- **WHEN** the user presses `i`
- **THEN** every checked choice becomes unchecked and every unchecked choice becomes checked

#### Scenario: Submit in declaration order
- **WHEN** the user confirms a mixture of checked choices
- **THEN** the capability returns their values in declared choice order

### Requirement: Distinct cancellation
The interactive checklist SHALL support cancellation through Ctrl+C and Ctrl+Q and
SHALL distinguish cancellation from confirming an empty selection. Required policy
SHALL reject a confirmed empty selection but SHALL preserve cancellation as its own
result.

#### Scenario: Cancel the checklist
- **WHEN** the user presses Ctrl+C or Ctrl+Q
- **THEN** the result is marked cancelled with no selected values

#### Scenario: Confirm an optional empty selection
- **WHEN** selection is optional and the user confirms with no checked choices
- **THEN** the result is empty and not cancelled

#### Scenario: Reject a required empty selection
- **WHEN** selection is required and the user attempts to confirm with no checked choices
- **THEN** the checklist remains active and communicates that a selection is required

### Requirement: Recoverable terminal lifecycle
The capability SHALL restore terminal input mode and cursor visibility after normal
submission, cancellation, or an exception. Repainting SHALL update the active menu
instead of appending a complete copy for each key press.

#### Scenario: Restore after submission
- **WHEN** an interactive selection is submitted normally
- **THEN** the terminal is returned to its prior mode with the cursor visible

#### Scenario: Restore after failure
- **WHEN** cancellation or an exception interrupts interaction
- **THEN** terminal restoration still occurs before control returns to the caller

### Requirement: Constrained dependency-free experience
The capability SHALL provide its selection policy and supported Windows and POSIX
terminal interaction without requiring a CLI framework or third-party runtime
package. Unsupported terminal capabilities SHALL fail clearly rather than leaving a
partially initialized interaction.

#### Scenario: Use values outside an agent CLI
- **WHEN** a caller supplies ordinary application values and compatible terminal streams
- **THEN** selection works without Agent Router, Typer, Questionary, or Prompt Toolkit

#### Scenario: Reject an unsupported interactive terminal
- **WHEN** interactive selection is requested but the terminal cannot provide the required input or repaint behavior
- **THEN** the capability fails before presenting a partial checklist

### Requirement: Runnable selection demonstration
The capability SHALL provide a module entry point that demonstrates the public
selection lifecycle with illustrative agent choices. The demonstration SHALL accept
repeatable explicit `--agent` values, support optional empty selection, report the
selected values, and use distinct success, cancellation, and error exit statuses.

#### Scenario: Open the demonstration checklist
- **WHEN** a person runs the case11 module without explicit values in an interactive terminal
- **THEN** the demonstration opens the live agent checklist and reports the confirmed values

#### Scenario: Demonstrate explicit precedence
- **WHEN** a caller repeats valid `--agent` options
- **THEN** the demonstration reports their first-seen unique values without opening the checklist

#### Scenario: Report cancellation and errors
- **WHEN** the demonstration is cancelled or cannot complete selection
- **THEN** it writes a concise diagnostic and exits with a status distinct from success

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
