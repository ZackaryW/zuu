## 1. Closed input

- [x] 1.1 Add bounded reader and lifecycle regressions for EOF, truncated keys, Windows console loss, and unsupported bytes; record failing EOF checks before implementation.
- [x] 1.2 Implement terminal-error guards in both readers and preserve ignored bytes/timeouts; verify reader tests, session restoration, real pipe EOF, and a time-limited native Windows console-loss probe.

## 2. Rendering resources

- [x] 2.1 Add regressions for repeated empty submits, unchanged navigation with resize, and large/long constrained layouts; observe duplicate-output and excessive-work failures before implementation.
- [x] 2.2 Suppress identical successful frames and bound layout/text fitting; verify new regressions and existing Unicode, viewport, finish, selection, and resize tests.

## 3. Completion

- [x] 3.1 Document EOF errors, repaint behavior, and unattended input/capture guidance; verify examples and error descriptions against the implementation.
- [x] 3.2 Run the full repository suite, native Windows screen smoke check, and strict OpenSpec validation; record RED/GREEN evidence, scenario coverage, and the original incident's remaining uncertainty in a verification report.
