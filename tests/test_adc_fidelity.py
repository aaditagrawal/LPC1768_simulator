"""Independent NXP UM10360 chapter 29 / datasheet Fig.28 ADC probes.

Nominal inputs are the integer step centers in Fig.28, not values generated
by the simulator. Threshold probes use k-0.5 LSB +/- 1e-5 LSB; exact ties
are deliberately excluded because physical comparator equality is unspecified.
"""
from pathlib import Path
import json
import random
import struct

import pytest

from simulator.compiler import Compiler
from simulator.engine import Machine

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x40034000
DONE, OVERRUN, PDN, BURST = 1 << 31, 1 << 30, 1 << 21, 1 << 16
LSB = 3.3 / 4096
_ledger_started = False


def record_cases(cases):
    """Per-stimulus evidence; unit count and enumerated observation count differ."""
    global _ledger_started
    target = ROOT / 'build/audit-adc-cases.jsonl'
    target.parent.mkdir(exist_ok=True)
    with target.open('a' if _ledger_started else 'w', encoding='utf-8') as out:
        for case in cases:
            out.write(json.dumps(case, separators=(',', ':')) + '\n')
    _ledger_started = True


def case(test_id, channel, voltage, expected, raw):
    expected_raw = DONE | (channel << 24) | (expected << 4)
    return dict(id=test_id, lab=10, input_volts=voltage, channel=channel,
                adcr=PDN | (1 << channel) | (1 << 24), pclk_div=4,
                event_core_cycles=260, wiring=dict(pin_function=3, JP18='2-3', PCADC=1),
                expected_code=expected, observed_code=(raw >> 4) & 4095,
                expected_register=expected_raw, observed_register=raw,
                status='PASS' if raw == expected_raw else 'FAIL',
                source='NXP LPC176x Rev9.10 Fig28; UM10360 ch29',
                confidence='high: ideal transfer; physical accuracy UNVERIFIED')


def machine():
    m = Machine((ROOT / 'examples/idle.hex').read_text())
    m.write_word(m.SC + 0xC4, m.read_word(m.SC + 0xC4) | (1 << 12))
    m.write_word(m.PIN + 0x0C, 0xF0000000)
    m.write_word(m.PIN + 0x4C, 0xA0000000)  # both analog pins, no pull
    m.board.set_jumper('JP18', '2-3')
    return m


def advance(m, core_cycles):
    # Offline time is instruction-derived core cycles; ADC clocks default /4.
    m.ticks += core_cycles


def start(m, channel, divider=0, burst=False):
    m.write_word(BASE, PDN | (1 << channel) | (divider << 8) |
                 (BURST if burst else 1 << 24))


def sample(m, channel, voltage):
    m.board.pots[channel] = voltage
    start(m, channel)
    advance(m, 65 * 4)
    return m.read_word(BASE + 4)


@pytest.mark.parametrize('channel', [4, 5])
def test_all_4096_ideal_step_centers(channel):
    m = machine()
    mismatches = []
    cases = []
    for expected in range(4096):
        raw = sample(m, channel, expected * LSB)
        cases.append(case(f'nominal-ch{channel}-{expected}', channel, expected * LSB, expected, raw))
        actual = (raw >> 4) & 4095
        if actual != expected or not raw & DONE or (raw >> 24) & 7 != channel:
            mismatches.append((expected, hex(raw)))
    record_cases(cases)
    assert not mismatches, f'{len(mismatches)}/4096 mismatches; first: {mismatches[:8]}'


@pytest.mark.parametrize('channel', [4, 5])
def test_both_sides_of_all_4095_ideal_transitions(channel):
    m = machine()
    mismatches = []
    cases = []
    for upper in range(1, 4096):
        for side, expected in [(-1, upper - 1), (1, upper)]:
            voltage = (upper - 0.5 + side * 1e-5) * LSB
            raw = sample(m, channel, voltage)
            cases.append(case(f'transition-ch{channel}-{upper}-{side}', channel, voltage, expected, raw))
            if (raw >> 4) & 4095 != expected:
                mismatches.append((upper, side, expected, (raw >> 4) & 4095))
    record_cases(cases)
    assert not mismatches, f'{len(mismatches)}/8190 mismatches; first: {mismatches[:8]}'


def test_reset_registers_documented_values():
    m = Machine((ROOT / 'examples/idle.hex').read_text())
    assert m.read_word(BASE) == 1
    assert m.read_word(BASE + 0x0C) == 0x100
    assert m.read_word(BASE + 0x34) == 0xF00
    assert m.read_word(BASE + 0x30) == 0


@pytest.mark.parametrize('divider', [0, 1, 7, 255])
@pytest.mark.parametrize('pclksel,pclkdiv', [(0, 4), (1, 1), (2, 2), (3, 8)])
def test_conversion_completes_after_65_divided_adc_clocks(divider, pclksel, pclkdiv):
    m = machine()
    m.write_word(m.SC + 0x1A8, pclksel << 24)
    start(m, 5, divider)
    assert not m.read_word(BASE + 4) & DONE
    advance(m, 65 * (divider + 1) * pclkdiv - 1)
    assert not m.read_word(BASE + 4) & DONE
    advance(m, 1)
    assert m.read_word(BASE + 4) & DONE
    assert not m.read_word(BASE + 4) & DONE


def test_single_shot_does_not_reconvert_by_reading_and_preserves_result():
    m = machine()
    assert ((sample(m, 5, 1.65) >> 4) & 4095) == 2048
    m.board.pots[5] = 3.3
    advance(m, 26000)
    raw = m.read_word(BASE + 4)
    assert not raw & DONE
    assert (raw >> 4) & 4095 == 2048


def test_write_adcr_clears_global_done_but_not_channel_done():
    m = machine()
    start(m, 5)
    advance(m, 260)
    assert m.read_word(BASE + 0x30) & (1 << 5)
    m.write_word(BASE, PDN | (1 << 5))
    assert not m.read_word(BASE + 4) & DONE
    assert m.read_word(BASE + 0x24) & DONE


def test_global_and_channel_reads_clear_only_their_own_flags():
    m = machine()
    start(m, 4)
    advance(m, 260)
    assert m.read_word(BASE + 4) & DONE
    assert m.read_word(BASE + 0x20) & DONE
    assert not m.read_word(BASE + 0x20) & DONE
    start(m, 5)
    advance(m, 260)
    assert m.read_word(BASE + 0x24) & DONE
    assert m.read_word(BASE + 4) & DONE
    assert not m.read_word(BASE + 4) & DONE


def test_burst_scan_order_overrun_adstat_and_read_side_effects():
    m = machine()
    m.board.pots = {4: 0.0, 5: 3.3}
    m.write_word(BASE + 0x0C, 1 << 4)
    m.write_word(BASE, PDN | BURST | (1 << 4) | (1 << 5))
    advance(m, 260)
    first = m.read_word(BASE + 4)
    assert first & DONE and (first >> 24) & 7 == 4
    advance(m, 260)
    second = m.read_word(BASE + 4)
    assert second & DONE and (second >> 24) & 7 == 5
    assert (second >> 4) & 4095 == 4095
    advance(m, 260)
    status = m.read_word(BASE + 0x30)
    assert status & 0x30 == 0x30
    assert status & (1 << 12)
    assert status & (1 << 16)
    assert m.read_word(BASE + 0x30) == status  # ADSTAT is nondestructive.
    raw = m.read_word(BASE + 0x20)
    assert raw & (DONE | OVERRUN) == DONE | OVERRUN
    assert not m.read_word(BASE + 0x20) & (DONE | OVERRUN)
    assert not m.read_word(BASE + 0x30) & ((1 << 4) | (1 << 12) | (1 << 16))


def test_burst_global_overrun_clears_on_read_without_creating_conversion():
    m = machine()
    start(m, 5, burst=True)
    advance(m, 520)
    raw = m.read_word(BASE + 4)
    assert raw & (DONE | OVERRUN) == DONE | OVERRUN
    assert not m.read_word(BASE + 4) & (DONE | OVERRUN)
    assert m.read_word(BASE + 0x24) & (DONE | OVERRUN) == DONE | OVERRUN


def test_burst_stop_finishes_current_conversion():
    m = machine()
    start(m, 5, burst=True)
    advance(m, 100)
    m.write_word(BASE, PDN | (1 << 5))
    advance(m, 160)
    assert m.read_word(BASE + 4) & DONE
    advance(m, 260)
    assert not m.read_word(BASE + 4) & DONE


@pytest.mark.parametrize('trigger', range(2, 8))
def test_hardware_trigger_selections_do_not_start_immediately(trigger):
    m = machine()
    m.write_word(BASE, PDN | (1 << 5) | (trigger << 24))
    advance(m, 26000)
    assert not m.read_word(BASE + 4) & DONE


def test_burst_with_nonzero_start_does_not_start():
    m = machine()
    m.write_word(BASE, PDN | BURST | (1 << 5) | (1 << 24))
    advance(m, 26000)
    assert not m.read_word(BASE + 4) & DONE


@pytest.mark.parametrize('gate', ['pconp', 'pdn'])
def test_power_gate_prevents_conversion(gate):
    m = machine()
    if gate == 'pconp':
        m.write_word(m.SC + 0xC4, m.read_word(m.SC + 0xC4) & ~(1 << 12))
        start(m, 5)
    else:
        m.write_word(BASE, (1 << 5) | (1 << 24))
    advance(m, 26000)
    assert not m.read_word(BASE + 4) & DONE


def test_pot4_jumper_and_mux_are_required_for_driven_pot_voltage():
    m = machine()
    for channel in [4, 5]:
        m.board.pots[channel] = 3.3
    assert (sample(m, 5, 3.3) >> 4) & 4095 == 4095
    for position in ['open', '1-2', '2-3']:
        m.board.set_jumper('JP18', position)
        assert (sample(m, 4, 3.3) >> 4) & 4095 == (4095 if position == '2-3' else 0)
        assert (sample(m, 5, 3.3) >> 4) & 4095 == 4095
    m.write_word(m.PIN + 0x0C, 0)
    assert (sample(m, 4, 3.3) >> 4) & 4095 == 0
    assert (sample(m, 5, 3.3) >> 4) & 4095 == 0


def test_irq_enable_global_selection_takes_precedence_and_stat_reflects_it():
    m = machine()
    m.write_word(BASE + 0x0C, (1 << 8) | (1 << 4))
    start(m, 5)
    advance(m, 260)
    m.read_word(BASE + 0x30)
    assert m.pending_irq & (1 << 22)
    m.read_word(BASE + 4)  # clears global source despite unread channel 5
    assert not m.read_word(BASE + 0x30) & (1 << 16)
    m.write_word(BASE + 0x0C, 1 << 4)
    assert not m.read_word(BASE + 0x30) & (1 << 16)
    m.write_word(BASE + 0x0C, 1 << 5)
    assert m.read_word(BASE + 0x30) & (1 << 16)


def test_clock_or_power_change_accounts_previous_conversion_interval():
    m = machine()
    start(m, 5)
    advance(m, 260)
    # Conversion finished before the peripheral was gated; data must remain.
    m.write_word(m.SC + 0xC4, m.read_word(m.SC + 0xC4) & ~(1 << 12))
    assert m.read_word(BASE + 4) & DONE


def test_final_inflight_burst_conversion_retains_overrun_semantics():
    m = machine()
    start(m, 5, burst=True)
    advance(m, 360)  # one complete and another 100 core clocks into conversion
    m.write_word(BASE, PDN | (1 << 5))
    advance(m, 160)
    raw = m.read_word(BASE + 0x24)
    assert raw & (DONE | OVERRUN) == DONE | OVERRUN


def test_overrun_remains_sticky_until_its_data_register_is_read():
    m = machine()
    start(m, 5, burst=True)
    advance(m, 520)
    # Complete two conversions without consuming either result register.
    assert m.read_word(BASE + 0x30) & (1 << 13)
    m.write_word(BASE, PDN | (1 << 5))
    advance(m, 260)
    start(m, 5)
    advance(m, 260)
    assert m.read_word(BASE + 4) & OVERRUN
    assert m.read_word(BASE + 0x24) & OVERRUN
    assert not m.read_word(BASE + 4) & OVERRUN
    assert not m.read_word(BASE + 0x24) & OVERRUN


def test_trim_boot_bits_locked_and_offset_is_writable():
    m = machine()
    m.write_word(BASE + 0x34, 0xFFFFFFFF)
    assert m.read_word(BASE + 0x34) == 0xFF0
    m.write_word(BASE + 0x34, 0)
    assert m.read_word(BASE + 0x34) == 0xF00


def test_realtime_adc_conversion_and_pause_preserve_remaining_time():
    now = [0]
    m = Machine((ROOT / 'examples/idle.hex').read_text(), realtime=True, clock_ns=lambda: now[0])
    m.write_word(m.SC + 0xC4, m.read_word(m.SC + 0xC4) | (1 << 12))
    m.write_word(m.PIN + 0x0C, 0xC0000000)
    m.resume_clock()
    start(m, 5)
    now[0] = 64999  # reset core=4MHz, ADC=1MHz; 65 ADC clocks = 65000ns
    assert not m.read_word(BASE + 4) & DONE
    m.pause_clock()
    now[0] += 1000000000
    assert not m.read_word(BASE + 4) & DONE
    m.resume_clock()
    now[0] += 1
    assert m.read_word(BASE + 4) & DONE


def test_burst_large_time_jump_retains_scan_phase_and_flags():
    m = machine()
    m.board.pots = {4: 0.0, 5: 3.3}
    m.write_word(BASE, PDN | BURST | 0x30)
    # >3.8 billion conversions: finite work is expected for a static input.
    advance(m, 10**12 + 123)
    completed = (10**12 + 123) // 260
    expected_channel = 4 if completed % 2 else 5
    raw = m.read_word(BASE + 4)
    assert (raw >> 24) & 7 == expected_channel
    assert (raw >> 4) & 4095 == (0 if expected_channel == 4 else 4095)
    assert raw & (DONE | OVERRUN) == DONE | OVERRUN
    assert m.read_word(BASE + 0x30) & 0x3030 == 0x3030


PROBE = '''#include <LPC17xx.h>
int main(void) {
 volatile unsigned *box=(void*)0x10007000; unsigned old=0,raw,ch;
 LPC_SC->PCONP|=1u<<12; LPC_PINCON->PINSEL3|=0xF0000000;
 LPC_PINCON->PINMODE3=(LPC_PINCON->PINMODE3&~0xF0000000)|0xA0000000;
 while(1) {if(box[0]!=old) {old=box[0];ch=box[1];
  LPC_ADC->ADCR=(1u<<ch)|(1u<<8)|(1u<<21)|(1u<<24);
  do {raw=LPC_ADC->ADGDR;} while(!(raw&(1u<<31)));
  box[2]=raw; box[3]=old;
 }} }
'''


@pytest.fixture(scope='module')
def probe_hex():
    return Compiler().compile(PROBE).hex


def command(m, sequence, channel):
    m.uc.mem_write(0x10007000, struct.pack('<II', sequence, channel))
    for _ in range(10):
        m.run(1000)
        raw, ack = struct.unpack('<II', bytes(m.uc.mem_read(0x10007008, 8)))
        if ack == sequence:
            return raw
    raise AssertionError(f'ADC firmware timed out: {m.snapshot()}')


def test_compiled_c_both_channels_required_voltages_and_random_switching(probe_hex):
    m = Machine(probe_hex)
    m.board.set_jumper('JP18', '2-3')
    # Explicit independent integer expectations from Fig28; no production helpers.
    vectors = [(0, 0), (0.1, 124), (0.5, 621), (1.0, 1241), (1.65, 2048),
               (2.0, 2482), (2.5, 3103), (3.0, 3724), (3.3, 4095)]
    sequence = 0
    for channel in [4, 5]:
        for voltage, expected in vectors:
            m.board.pots[channel] = voltage
            sequence += 1
            raw = command(m, sequence, channel)
            assert (raw >> 4) & 4095 == expected
            assert (raw >> 24) & 7 == channel
    rng = random.Random(1768)
    for _ in range(100):
        channel, expected = rng.choice([4, 5]), rng.randrange(4096)
        m.board.pots[channel] = expected * LSB
        sequence += 1
        assert (command(m, sequence, channel) >> 4) & 4095 == expected


@pytest.mark.parametrize('mutation', ['control', 'power', 'mux', 'channel', 'pdn', 'start', 'poll'])
def test_compiled_c_adc_mutations_are_observable(mutation):
    source = PROBE
    if mutation == 'power':
        source = source.replace('LPC_SC->PCONP|=1u<<12;', '')
    elif mutation == 'mux':
        source = source.replace('LPC_PINCON->PINSEL3|=0xF0000000;', '')
    elif mutation == 'channel':
        source = source.replace('(1u<<ch)', '(1u<<(ch==4?5:4))')
    elif mutation == 'pdn':
        source = source.replace('|(1u<<21)', '')
    elif mutation == 'start':
        source = source.replace('|(1u<<24)', '')
    elif mutation == 'poll':
        source = source.replace('do {raw=LPC_ADC->ADGDR;} while(!(raw&(1u<<31)));',
                                'raw=LPC_ADC->ADGDR;')
    m = Machine(Compiler().compile(source).hex)
    m.board.set_jumper('JP18', '2-3')
    m.board.pots = {4: 1234 * LSB, 5: 3000 * LSB}
    try:
        raw = command(m, 1, 4)
        success = (raw >> 4) & 4095 == 1234 and bool(raw & DONE)
    except AssertionError:
        success = False
    assert success == (mutation == 'control'), f'undetected mutation: {mutation}'


def test_corrected_adc_examples_use_legal_full_resolution_clock(difference_hex):
    # Execute actual examples and inspect their configured clocks and ADCR,
    # rather than checking for a particular expression in the C source.
    adc5 = Compiler().compile((ROOT / 'examples/lab10_adc5.c').read_text()).hex
    for firmware in [adc5, difference_hex]:
        m = Machine(firmware)
        m.board.set_jumper('JP18', '2-3')
        for _ in range(30):
            m.run(2000)
            if m.read_word(BASE) & PDN:
                break
        assert m.read_word(BASE) & PDN
        pclk_div = (4, 1, 2, 8)[(m.read_word(m.SC + 0x1A8) >> 24) & 3]
        divider = ((m.read_word(BASE) >> 8) & 255) + 1
        assert m.core_clock_hz() / pclk_div / divider <= 13_000_000
        assert m.read_word(m.PIN + 0x4C) & 0xF0000000 == 0xA0000000


@pytest.mark.parametrize('mode', ['global', 'channel', 'mixed_read_mutation'])
def test_compiled_adc_interrupt_completes_without_polling_mmio(mode):
    source = '''#include <LPC17xx.h>
    void ADC_IRQHandler(void) {
      volatile unsigned *box=(void*)0x10007000;
      box[1]=LPC_ADC->ADGDR; box[0]++;
    }
    int main(void) {
      LPC_SC->PCONP|=1u<<12; LPC_PINCON->PINSEL3|=0xC0000000;
      LPC_PINCON->PINMODE3=(LPC_PINCON->PINMODE3&~0xC0000000)|0x80000000;
      LPC_ADC->ADINTEN=1u<<5; NVIC_EnableIRQ(ADC_IRQn);
      LPC_ADC->ADCR=(1u<<5)|(1u<<8)|(1u<<21)|(1u<<24);
      while(1) {}
    }'''
    if mode == 'global':
        source = source.replace('ADINTEN=1u<<5', 'ADINTEN=1u<<8')
    elif mode == 'channel':
        source = source.replace('box[1]=LPC_ADC->ADGDR;', 'box[1]=LPC_ADC->ADDR5;')
    m = Machine(Compiler().compile(source).hex)
    m.board.pots[5] = 1234 * LSB
    for _ in range(20):
        m.run(1000)
    count, raw = struct.unpack('<II', bytes(m.uc.mem_read(0x10007000, 8)))
    if mode == 'mixed_read_mutation':
        # UM10360 warns that global/channel flags can get out of sync: reading
        # GDR cannot acknowledge a per-channel interrupt. The IRQ must repeat.
        assert count > 1
    else:
        assert count == 1
        assert raw & DONE
        assert (raw >> 4) & 4095 == 1234


@pytest.fixture(scope='module')
def difference_hex():
    return Compiler().compile((ROOT / 'examples/lab10_difference.c').read_text()).hex


@pytest.mark.parametrize('a,b,expected', [(0, 0, 0), (3.3, 3.3, 0),
    (1.65, 1.65, 0), (3.3, 0, 4095), (0, 3.3, -4095),
    (1.65, 0, 2048), (0, 1.65, -2048), (3.3, 1.65, 2047), (1.65, 3.3, -2047)])
def test_compiled_adc_difference_actual_lcd(difference_hex, a, b, expected):
    m = Machine(difference_hex)
    m.board.connect('CND', 'CNAD')
    m.board.set_jumper('JP5', 'closed')
    m.board.set_jumper('JP16', 'closed')
    m.board.set_jumper('JP18', '2-3')
    m.board.pots = {4: a, 5: b}
    expected_text = f'{expected} counts'.ljust(16)
    for _ in range(30):
        m.run(20000)
        if m.snapshot()['lcd'][1] == expected_text:
            return
    assert m.snapshot()['lcd'][1] == expected_text
