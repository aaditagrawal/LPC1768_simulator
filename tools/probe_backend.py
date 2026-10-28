"""Throwaway architecture gate: installed Keil -> real HEX -> Unicorn GPIO."""
from pathlib import Path
import subprocess
import sys
from io import StringIO

from intelhex import IntelHex
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS
from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_PC

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build' / 'probe'
OUT.mkdir(parents=True, exist_ok=True)
KEIL = Path('C:/Keil/ARM')
BIN = KEIL / 'ARMCC/bin'
SOURCE = '''#include <LPC17xx.h>
int main(void) {
 SystemInit(); SystemCoreClockUpdate();
 LPC_GPIO0->FIODIR = 0xFF0;
 while(1) { LPC_GPIO0->FIOSET=0x10; LPC_GPIO0->FIOCLR=0x10; }
}
'''
(OUT / 'main.c').write_text(SOURCE)

def run(exe, *args):
    p = subprocess.run([str(BIN / exe), *map(str, args)], cwd=OUT,
                       capture_output=True, text=True, timeout=30)
    if p.stdout or p.stderr:
        print(p.stdout, p.stderr)
    if p.returncode:
        raise RuntimeError(f'{exe}: {p.returncode}')

flags = ['--cpu', 'Cortex-M3', '--thumb', '--c99', '-O0', '-g',
         '--library_type=microlib', '-I', KEIL/'INC/NXP/LPC17xx',
         '-I', KEIL/'CMSIS/Include', '-c']
run('armcc.exe', *flags, 'main.c', '-o', 'main.o')
run('armcc.exe', *flags, KEIL/'Startup/NXP/LPC17xx/system_LPC17xx.c', '-o', 'system.o')
run('armasm.exe', '--cpu', 'Cortex-M3', '-g', '--pd', '__MICROLIB SETA 1',
    KEIL/'Startup/NXP/LPC17xx/startup_LPC17xx.s', '-o', 'startup.o')
run('armlink.exe', '--cpu', 'Cortex-M3', '--ro_base', '0', '--rw_base', '0x10000000',
    '--first', 'startup.o(RESET)', '--entry', 'Reset_Handler', '--library_type=microlib',
    'startup.o', 'system.o', 'main.o', '-o', 'firmware.axf')
run('fromelf.exe', '--i32combined', '--output', 'firmware.hex', 'firmware.axf')
ih = IntelHex(StringIO((OUT/'firmware.hex').read_text()))
uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
uc.mem_map(0, 0x80000)
uc.mem_map(0x10000000, 0x8000)
uc.mem_map(0x2007C000, 0x8000)
for start, end in ih.segments():
    uc.mem_write(start, ih.tobinarray(start=start, end=end-1).tobytes())
regs, events = {}, []

def read(uc, off, size, data):
    addr = data + off
    if addr == 0x400FC1A0:
        return regs.get(addr, 0) | 0x40
    if addr == 0x400FC088:
        return regs.get(0x400FC084, 0) | (regs.get(0x400FC080, 0)<<24) | (1<<26)
    if addr == 0x400FC0A8:
        return regs.get(0x400FC0A4, 0) | (regs.get(0x400FC0A0, 0)<<8) | (1<<10)
    return regs.get(addr, 0)

def write(uc, off, size, value, data):
    addr = data + off
    regs[addr] = value
    if addr in (0x2009C018, 0x2009C01C):
        if len(events) < 12:
            events.append({'address': hex(addr), 'value': hex(value)})

for base, size in [(0x40000000, 0x100000), (0x2009C000, 0x1000), (0xE000E000, 0x2000)]:
    uc.mmio_map(base, size, read, base, write, base)
sp, pc = [int.from_bytes(uc.mem_read(a, 4), 'little') for a in (0, 4)]
uc.reg_write(UC_ARM_REG_SP, sp)
uc.emu_start(pc | 1, 0x80000, count=100000)
print({'sp': hex(sp), 'reset': hex(pc), 'pc': hex(uc.reg_read(UC_ARM_REG_PC)),
       'GPIO_writes': events})
assert len(events) >= 2, 'Backend gate FAILED: no actual firmware GPIO writes'
print('BACKEND GATE PASSED: genuine Keil HEX executed; GPIO SET/CLR observed.')
