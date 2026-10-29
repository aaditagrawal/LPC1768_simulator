"""Replay selected audit regressions against an isolated original Git snapshot.

This intentionally produces failed hardware assertions. It never changes the
working tree's simulator or branch. Traces are kept separate from passing runs.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = '5069731bab7ab6e45c917cca8d43eb342abd13ec'
OUT = ROOT / 'build/hardware-audit/original-replay'


def main():
    snapshot = OUT / 'snapshot'
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE],
                                    cwd=ROOT, text=True).splitlines()
    for name in names:
        if not (name.startswith('simulator/') or name == 'board/mapping.json'
                or name.startswith('examples/')):
            continue
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT))
    report = OUT / 'expected-failures.xml'
    nodes = [
        'tests/test_display_fidelity.py::test_lcd_clear_restores_increment_mode',
        'tests/test_display_fidelity.py::test_lcd_return_home_accepts_dont_care_low_bit',
        'tests/test_display_fidelity.py::test_lcd_ddram_boundary_write_wrap',
        'tests/test_display_fidelity.py::test_lcd_entry_mode_shift_moves_display',
        'tests/test_display_fidelity.py::test_keypad_row_isolation_diodes_prevent_low_row_sinking',
        'tests/test_display_fidelity.py::test_decoder_inputs_have_documented_external_pullups',
        'tests/test_pwm_fidelity.py::test_pwm_ler_waits_for_cycle_boundary_and_retains_pending_bits',
        'tests/test_pwm_fidelity.py::test_pwm_counter_uses_one_based_cycle_without_losing_a_period_clock',
        'tests/test_execution_fidelity.py::test_gpio_open_drain_high_releases_pin_low_drives_pin',
        'tests/test_adc_fidelity.py::test_reset_registers_documented_values',
        'tests/test_adc_fidelity.py::test_conversion_completes_after_65_divided_adc_clocks',
    ]
    env = dict(os.environ, LPC_AUDIT_EVIDENCE_DIR=str(OUT / 'evidence'))
    code = ('import sys;sys.path.insert(0,sys.argv[1]);import pytest;'
            'raise SystemExit(pytest.main(sys.argv[2:]))')
    with (OUT / 'replay.log').open('w', encoding='utf-8') as log:
        result = subprocess.run([sys.executable, '-c', code, str(snapshot), '-q',
                                 '-p', 'no:cacheprovider', '--junitxml=' + str(report), *nodes],
                                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    suite = ET.parse(report).getroot().find('testsuite')
    summary = {'revision': BASE, 'pytest_exit_code': result.returncode,
               **{key: int(suite.get(key, 0)) for key in ('tests', 'failures', 'errors', 'skipped')},
               'meaning': 'Expected historical failures, separate from final regression results'}
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return 0 if summary['failures'] > 0 and not summary['errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
