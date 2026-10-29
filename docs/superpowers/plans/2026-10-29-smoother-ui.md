# Reduce unnecessary UI rendering

**Goal:** Keep the 50 ms display update cadence while reducing browser work, with the examination practice checkout untouched.

**Architecture:** Compare the fields actually presented by the UI before publishing a fetched snapshot to React. Internal CPU counters and GPIO diagnostics remain available through the API but do not trigger board reconciliation. Preserve physical input serialization, stale-response guards, clocks, wiring, and visible output precision.

**Tech stack:** Existing React, TypeScript, Playwright and Flask; no added dependencies.

**Constraints:** Develop in the sibling `lpc_simulator-performance` worktree on `perf/smoother-ui`, using its own dependencies, build and runtime on port 8879. Never run test requests against 8765. Keep the current appearance and hardware behavior.

1. Build the unchanged worktree and run the existing browser suite as an isolation baseline.
2. Measure browser main-thread CPU at 50 ms with timer-driven LED blinking.
3. Add regression coverage for unchanged visible snapshots and every visible output/control/status field; verify a failing regression before implementation.
4. Publish state only when the visible snapshot changes. Verify real browser interactions, error/status updates and delayed-response handling.
5. Repeat the same benchmark and browser suite; record the scope and limitations of the result. Verify the practice checkout and its build hashes and server PID are unchanged.

**Review focus:** Do not round PWM/pot values or suppress real output, warnings, firmware diagnostics or input changes. Tests and benchmarks must be pinned to the isolated URL.
