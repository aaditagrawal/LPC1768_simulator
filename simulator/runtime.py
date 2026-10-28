"""One bounded firmware worker; all mutations serialize with CPU execution."""
from __future__ import annotations
from pathlib import Path
import json
import threading
import time

from .engine import Machine, FirmwareError
from .compiler import Compiler
from .board import MAPPING

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / 'examples/catalog.json').read_text(encoding='utf-8'))


class Runtime:
    def __init__(self, start_worker=True, *, realtime=None):
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.closed = threading.Event()
        self.realtime = start_worker if realtime is None else realtime
        self.machine = Machine((ROOT / 'examples/idle.hex').read_text(), realtime=self.realtime)
        self.loaded = False
        self.status = 'empty'
        self.name = 'No firmware loaded'
        self.diagnostics = 'Compile Embedded C or upload an Intel HEX file.'
        self.compiler = Compiler()
        self.thread = None
        if start_worker:
            self.thread = threading.Thread(target=self._worker, name='lpc1768-cpu', daemon=True)
            self.thread.start()

    def _worker(self):
        while not self.closed.is_set():
            self.wake.wait(.1)
            if not self.wake.is_set():
                continue
            with self.lock:
                if self.status == 'running':
                    try:
                        self.machine.run(20000, timeout_us=1000)
                    except FirmwareError as e:
                        self.status = 'error'
                        self.diagnostics = str(e)
                        self.wake.clear()
                        self.machine.pause_clock()
                else:
                    self.wake.clear()
            # Yield to API/input threads without adding a 2 ms floor to each
            # firmware slice (the user's timer polling interval can be 1 ms).
            time.sleep(0)

    def close(self):
        self.closed.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _replace(self, candidate):
        old = self.machine.board
        b = candidate.board
        b.cables = [c[:] for c in old.cables]
        b.jumpers = dict(old.jumpers)
        b.pots = dict(old.pots)
        b.sw2, b.sw2_pin = old.sw2, old.sw2_pin
        b.keys = set(old.keys)
        candidate.observe()
        self.machine = candidate

    def load(self, text, name='Uploaded HEX', diagnostics='HEX loaded and validated.'):
        candidate = Machine(text, realtime=self.realtime) # validation is atomic
        with self.lock:
            self._replace(candidate)
            self.loaded = True
            self.name, self.status = name, 'ready'
            self.diagnostics = diagnostics
            self.wake.clear()
            return self.snapshot()

    def compile(self, source):
        result = self.compiler.compile(source)
        state = self.load(result.hex, 'Compiled C program', result.diagnostics)
        return {'state':state,'hex':result.hex,'diagnostics':result.diagnostics}

    def control(self, action):
        with self.lock:
            if action in ('run','resume'):
                if not self.loaded:
                    raise ValueError('Compile or upload firmware before running.')
                if self.machine.error:
                    raise ValueError('Reset the firmware after a runtime error.')
                self.status = 'running'
                self.machine.resume_clock()
                self.wake.set()
            elif action == 'pause':
                self.machine.pause_clock()
                if self.status == 'running':
                    self.status = 'paused'
                self.wake.clear()
            elif action in ('stop','reset'):
                running = self.status == 'running' and action == 'reset'
                self._replace(Machine(self.machine.hex_text, realtime=self.realtime))
                self.status = 'running' if running else ('ready' if self.loaded else 'empty')
                self.diagnostics = 'MCU reset. Physical cables and jumper settings retained.'
                if running:
                    self.machine.resume_clock()
                    self.wake.set()
                else:
                    self.wake.clear()
            else:
                raise ValueError('Unknown runtime control.')
            return self.snapshot()

    def physical(self, data):
        with self.lock:
            b = self.machine.board
            action = data.get('action')
            if action == 'connect':
                b.connect(data.get('a'),data.get('b'))
            elif action == 'disconnect':
                if not isinstance(data.get('header'),str) or data.get('header') not in MAPPING['headers']:
                    raise ValueError('Unknown header.')
                b.disconnect(data['header'])
            elif action == 'jumper':
                b.set_jumper(data.get('name'),data.get('value'))
            elif action == 'switch':
                if not isinstance(data.get('pressed'),bool):
                    raise ValueError('Switch pressed must be true or false.')
                b.sw2 = data['pressed']
            elif action == 'key':
                key = data.get('key')
                if type(key) is not int or not 0 <= key < 16 or not isinstance(data.get('pressed'),bool):
                    raise ValueError('Key must be 0–15, with a boolean pressed state.')
                if data['pressed']:
                    b.keys.add(key)
                else:
                    b.keys.discard(key)
            elif action == 'pot':
                channel, voltage = data.get('channel'),data.get('voltage')
                if type(channel) is not int or channel not in (4,5) or type(voltage) not in (float,int) or not 0 <= voltage <= 3.3:
                    raise ValueError('POT voltage must be 0–3.3 V on channel 4 or 5.')
                b.pots[channel] = voltage
            elif action == 'sw2-profile':
                if data.get('pin') not in (7,9):
                    raise ValueError('SW2 profile must be CNB1 pin 7 or 9.')
                b.sw2_pin = data['pin']
                b._graph_key = None
            elif action == 'release-inputs':
                b.sw2 = False
                b.keys.clear()
            else:
                raise ValueError('Unknown physical input action.')
            self.machine.observe()
            return self.snapshot()

    def check(self, exercise):
        spec = next((e for e in CATALOG if e['id'] == exercise),None)
        if not spec:
            raise ValueError('Unknown exercise.')
        with self.lock:
            b = self.machine.board
            issues = []
            highlight = set()
            for cable in spec['cables']:
                if not any(set(cable) == set(c) for c in b.cables):
                    issues.append('Connect ' + ' ↔ '.join(cable))
                    highlight.update(cable)
            for name,setting in spec['jumpers'].items():
                if b.jumpers[name] != setting:
                    issues.append(f'Set {name} to {setting}')
                    highlight.add(name)
            if any('CNB1' in c for c in spec['cables']) and b.sw2_pin != 7:
                issues.append('This reference uses the lab SW2 profile: CNB1 pin 7.')
            for cable in b.cables:
                if not any(set(cable) == set(c) for c in spec['cables']):
                    issues.append('Extra cable: ' + ' ↔ '.join(cable) + '; verify it does not conflict.')
                    highlight.update(cable)
            return {'ok':not issues,'issues':issues,'highlight':sorted(highlight)}

    def snapshot(self):
        with self.lock:
            return {**self.machine.snapshot(),'status':self.status,'loaded':self.loaded,
                    'firmwareName':self.name,'diagnostics':self.diagnostics}
