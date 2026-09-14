## ADDED Requirements

### Requirement: Closed interactive input terminates selection
The capability SHALL report a recoverable terminal error when an active input source reaches end of input or reports loss of its console, including while consuming a multi-character key. It SHALL restore terminal modes and cursor visibility before returning control and SHALL NOT repeatedly retry that terminal condition. Unsupported input characters and a timeout waiting for an escape continuation SHALL remain ignorable input rather than end of input.

#### Scenario: Input closes while waiting for a key
- **WHEN** an active input source reports end of input or loss of its Windows console
- **THEN** selection terminates with a recoverable terminal error and performs session cleanup without reading again

#### Scenario: Input closes during a multi-character key
- **WHEN** input ends after an escape prefix or Windows extended-key prefix
- **THEN** selection reports the terminal error and restores the session instead of silently retrying

#### Scenario: Unsupported bytes and escape timeout
- **WHEN** input contains an unsupported non-ASCII byte or an escape prefix whose continuation is not ready
- **THEN** the checklist ignores that input and can still process a subsequent supported key

### Requirement: Rendering work follows visible output
The checklist SHALL avoid writing an identical consecutive frame when an action leaves its visible content unchanged. It SHALL continue checking terminal dimensions before deciding whether to repaint. Constrained layout SHALL avoid building complete offscreen choice rows or fully wrapping overflowing text before selecting the visible window.

#### Scenario: Repeated empty submissions
- **WHEN** required selection receives repeated Enter keys with nothing checked
- **THEN** validation appears once, subsequent identical frames emit no output, and later selection or cancellation still works

#### Scenario: Unchanged navigation and terminal resize
- **WHEN** navigation leaves the visible menu unchanged, such as moving within a single-choice list
- **THEN** no duplicate frame is written, but a changed terminal size is still handled under the resize contract

#### Scenario: Large collection in a small viewport
- **WHEN** a small supported viewport displays a large collection or extremely long question and labels
- **THEN** rendering constructs only a viewport-sized candidate frame and visible text prefixes while preserving focused-choice display and full-collection selection semantics
