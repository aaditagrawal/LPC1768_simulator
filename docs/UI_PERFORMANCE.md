# UI refresh cost

The UI still polls every 50 ms, with one request in flight. It now avoids publishing
a new React state when only internal execution diagnostics change. Visible LEDs,
LCD text, segment patterns, PWM, wiring, jumpers, inputs, warnings, errors and
runtime status continue to update at the existing cadence. Firmware execution
and peripheral timing are unchanged. No dependencies or animations were added.

## Local measurements (2026-10-29)

Headless Chromium, 1366 × 768, timer-driven LED edges every 250 ms. Each version
ran three 8-second samples after a 1-second warm-up per sample. Chrome DevTools
`Performance.getMetrics` with `threadTicks` measured browser main-thread task
time divided by elapsed time. Both versions used the same isolated server and
50 ms polling interval.

| Measurement | Before | After |
| --- | ---: | ---: |
| Main-thread CPU, mean, % of one core | 5.08% | 3.48% |
| Main-thread CPU, trial range | 4.32–5.82% | 3.38–3.64% |
| State responses per second, mean | 19.99 | 19.98 |
| Median visible edge interval, trial range | 246.8–250.6 ms | 247.4–251.2 ms |

This is about 32% less browser main-thread work in this workload. It measures
neither total browser/GPU CPU nor emulator CPU. Host load and firmware affect
results; this does not promise hard real-time frames, faster software delays,
or the same saving on every PC. The purpose is to free browser time without
slowing display sampling or hiding actual output changes.

## Isolated development

The examination practice app remains in `C:\Users\harsh\Downloads\lpc_simulator`
on port 8765. This work is in the sibling `lpc_simulator-performance` worktree,
branch `perf/smoother-ui`. Open that folder for further development.

From the development worktree, in PowerShell:

```powershell
npm.cmd run build
.\start-isolated.bat --no-browser
.\test-isolated.bat
$env:LPC_LAB_URL='http://127.0.0.1:8879'
node tools/benchmark_ui.mjs current
```

The benchmark loads test firmware and changes wiring only on port 8879; it
refuses the practice port. Its three samples are written to
`build/ui-benchmark-current.json`. The server, virtual environment, frontend
dependencies, build output and test artifacts are local to this worktree.
