# Native runtime setup

Install uv and Python 3.11–3.13, then run `uv sync --frozen` and
`uv run python -m pytest -ra`. The locked Zig package supplies the default
compiler; compilation does not need a JavaScript runtime. ARMASM support is a
subset, not a full ARM assembler. See `toolchain/README.md` for compiler
selection, target libraries, licenses, and hardware limitations.

The existing `start.bat` uses `tools/launch.py`, which synchronizes the locked
Python environment before starting. To build the existing local interface it
also needs Bun. Set `LPC_LAB_PORT` to choose the local server port. Regenerating
newlib with `tools/vendor_c_library.py` needs Bun or the optional zstandard
Python package. The checked-in target archives need no regeneration to compile.
Frozen application packaging is not included; this contribution supports the
source runtime only. CI declares a platform matrix, but only locally reported
results are verified until those jobs run.

The bundled curricular fixtures default to `fixtures/curricular`; set
`CURRICULAR_ES` for an optional external corpus. See its provenance manifest.
