"""Small fixed ten-conductor connection graph, derived from the ALS manual."""
from __future__ import annotations
from pathlib import Path
import json

MAPPING = json.loads((Path(__file__).resolve().parents[1] / 'board/mapping.json').read_text(encoding='utf-8'))


class Board:
    def __init__(self, machine):
        self.machine = machine
        self.cables = []
        self.jumpers = {k: 'open' for k in MAPPING['jumpers']}
        self.sw2 = False
        self.sw2_pin = 7
        self.keys = set()
        self.pots = {4: 1.65, 5: 1.65}
        self._graph_key = None
        self._groups = []
        self.warnings = []

    def connect(self, a, b):
        if not isinstance(a,str) or not isinstance(b,str) or a not in MAPPING['headers'] or b not in MAPPING['headers'] or a == b:
            raise ValueError('Select two different supported FRC headers.')
        if any(a in c or b in c for c in self.cables):
            raise ValueError('Each header can carry only one ribbon cable. Disconnect it first.')
        self.cables.append([a, b])
        self.machine.observe()

    def disconnect(self, header):
        self.cables = [c for c in self.cables if header not in c]
        self.machine.observe()

    def set_jumper(self, name, value):
        if not isinstance(name,str) or name not in MAPPING['jumpers'] or value not in MAPPING['jumpers'][name]['states']:
            raise ValueError('Unknown jumper or invalid shunt position.')
        self.jumpers[name] = value
        self.machine.observe()

    def _pin(self, header, pin):
        if header == 'CNB1' and pin in (6, 8):
            return 'SW2' if pin == self.sw2_pin - 1 else None
        node = MAPPING['headers'][header]['pins'][pin]
        if node == 'JP4_B':
            return 'P2.13' if self.jumpers['JP4'] == '1-2' else None
        if node == 'JP4_C':
            return 'P2.13' if self.jumpers['JP4'] == '2-3' else None
        if node == 'JP5_DATA':
            return 'P0.26' if self.jumpers['JP5'] == 'closed' else None
        return node

    def groups(self):
        key = (tuple(map(tuple, self.cables)), tuple(self.jumpers.values()),
               tuple(sorted(self.keys)), self.sw2_pin)
        if key == self._graph_key:
            return self._groups
        parents = {}
        def find(n):
            parents.setdefault(n, n)
            if parents[n] != n:
                parents[n] = find(parents[n])
            return parents[n]
        def union(a, b):
            if a is not None and b is not None:
                parents[find(a)] = find(b)
        for a, b in self.cables:
            for i in range(10):
                union(self._pin(a, i), self._pin(b, i))
        for k in self.keys:
            # ESD schematic PDF p42: D6-D9 isolate the four ROW connector
            # terminals from the switch buses. They are row diodes, not
            # individual key diodes; rectangle ghosting remains possible.
            union(f'MATRIX_ROW{k//4}', f'COL{k%4}')
        groups = {}
        for n in list(parents):
            groups.setdefault(find(n), []).append(n)
        self._groups = list(groups.values())
        self._graph_key = key
        return self._groups

    def signals(self):
        levels = {}
        warnings = []
        for a, b in self.cables:
            if MAPPING['headers'][a]['kind'] == MAPPING['headers'][b]['kind']:
                warnings.append(f'{a} ↔ {b}: two {MAPPING["headers"][a]["kind"]} headers; check pin compatibility.')
        groups = self.groups()
        drives = []
        pins = []
        for nodes in groups:
            strong, mcupins = [], []
            for n in nodes:
                if n == 'GND' or (n == 'SW2' and self.sw2):
                    strong.append(0)
                elif n == 'SW2':
                    strong.append(1)
                elif n.startswith('P') and '.' in n:
                    port, pin = map(int, n[1:].split('.'))
                    mcupins.append((port, pin))
                    out = self.machine.pin_output(port, pin)
                    if out is not None:
                        strong.append(out)
            drives.append(strong)
            pins.append(mcupins)
        # A driven HIGH conducts from ROW toward its matrix bus. A LOW on
        # an unselected row cannot sink a different row through this diode.
        # Weak internal MCU pulls do not overcome the external 15k pulldowns.
        high_rows = {r for r in range(4) if any(
            f'ROW{r}' in nodes and strong and min(strong) == 1
            for nodes, strong in zip(groups, drives))}
        for nodes, strong, mcupins in zip(groups, drives, pins):
            if any(f'MATRIX_ROW{r}' in nodes for r in high_rows):
                strong.append(1)
            if 0 in strong and 1 in strong:
                warnings.append('Conflicting driven levels on ' + ', '.join(nodes) + '; resolving LOW.')
            if strong:
                level = min(strong)
            elif any(n.startswith('COL') for n in nodes):
                level = 0 # documented external column pulldowns
            elif any(n.startswith('DIG') for n in nodes):
                # R75-R78, 10k to +5V, on U7 A-D (ESD schematic PDF p31).
                # Undriven selector inputs select 1111, disabling all digits.
                level = 1
            else:
                pulls = [self.machine.pin_pull(p, n) for p, n in mcupins]
                level = 0 if 0 in pulls else 1 if 1 in pulls else 0
            for n in nodes:
                # Weak MCU input pulls are observable by firmware, but cannot
                # drive a disconnected/multiplexed output peripheral.
                output_load = n.startswith(('LED','SEG','DIG','LCD')) or n == 'PWM_LED'
                levels[n] = level if strong or not output_load or n.startswith('DIG') else 0
        self.warnings = warnings
        return levels

    def inputs(self, port):
        levels = self.signals()
        value = 0
        for pin in range(32):
            node = f'P{port}.{pin}'
            default = self.machine.pin_pull(port, pin)
            bit = levels.get(node, default if default is not None else 0)
            value |= int(bool(bit)) << pin
        return value

    def has_signal_connection(self, prefix):
        return any(any(n.startswith(prefix) for n in group) and any(n.startswith('P') and '.' in n for n in group)
                   for group in self.groups())
