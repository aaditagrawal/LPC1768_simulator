"""Use an installed Keil toolchain; no proprietary binaries are copied."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


class CompileError(ValueError):
    pass


@dataclass
class Compilation:
    hex: str
    diagnostics: str


class Compiler:
    def __init__(self, keil_root: str | Path | None = None):
        self.root = Path(keil_root or os.environ.get('KEIL_ARM_ROOT', 'C:/Keil/ARM'))
        self.bin = self.root / 'ARMCC/bin'

    def info(self) -> dict:
        return {'available': (self.bin / 'armcc.exe').is_file(),
                'path': str(self.root), 'name': 'Installed Keil ARM Compiler (microlib)',
                'note': 'MDK Lite limits linked code/data to 32 KB. Uses local CMSIS and startup files.'}

    def compile(self, source: str) -> Compilation:
        if not self.info()['available']:
            raise CompileError('Keil ARM compiler not found. Set KEIL_ARM_ROOT to its ARM folder, or upload HEX.')
        if not source.strip() or len(source.encode('utf-8')) > 256_000:
            raise CompileError('C source must be nonempty and at most 256 KB.')
        diagnostics = []
        # The caller supplies text, never shell arguments or user-chosen filesystem paths.
        (ROOT / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='compile-', dir=ROOT / 'build') as td:
            out = Path(td)
            (out / 'main.c').write_text(source, encoding='utf-8')

            def run(exe: str, *args):
                try:
                    p = subprocess.run([str(self.bin / exe), *map(str, args)], cwd=out,
                                       capture_output=True, text=True, errors='replace', timeout=30,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                except (OSError, subprocess.TimeoutExpired) as e:
                    raise CompileError(f'{exe}: {e}') from e
                diagnostics.append(p.stdout + p.stderr)
                if p.returncode:
                    raise CompileError('\n'.join(diagnostics))

            flags = ['--cpu', 'Cortex-M3', '--thumb', '--c99', '-O0', '-g',
                     '--library_type=microlib', '-I', self.root / 'INC/NXP/LPC17xx',
                     '-I', self.root / 'CMSIS/Include', '-c']
            run('armcc.exe', *flags, 'main.c', '-o', 'main.o')
            run('armcc.exe', *flags, self.root / 'Startup/NXP/LPC17xx/system_LPC17xx.c', '-o', 'system.o')
            run('armasm.exe', '--cpu', 'Cortex-M3', '-g', '--pd', '__MICROLIB SETA 1',
                self.root / 'Startup/NXP/LPC17xx/startup_LPC17xx.s', '-o', 'startup.o')
            run('armlink.exe', '--cpu', 'Cortex-M3', '--ro_base', '0', '--rw_base', '0x10000000',
                '--first', 'startup.o(RESET)', '--entry', 'Reset_Handler', '--library_type=microlib',
                'startup.o', 'system.o', 'main.o', '-o', 'firmware.axf')
            run('fromelf.exe', '--i32combined', '--output', 'firmware.hex', 'firmware.axf')
            return Compilation((out / 'firmware.hex').read_text(),
                               '\n'.join(diagnostics).strip() or 'Keil compile and link succeeded.')
