"""Logical displays, updated from every GPIO transition, independently of UI FPS."""
from collections import deque


class LCD:
    def __init__(self):
        self.ram = [' '] * 128
        self.address = 0
        self.four_bit = False
        self.high = None
        self.display_on = False
        self.increment = 1
        self.entry_shift = False
        self.two_line = False
        self.enable = 0
        self.edges = 0
        self.shift = 0
        self.cgram = False

    def observe(self, enabled, en, rs, nibble):
        if not enabled:
            self.enable = 0
            self.high = None
            return
        if self.enable and not en:
            self.edges += 1
            if not self.four_bit:
                if not rs and nibble == 2:
                    self.four_bit = True
                    self.high = None
            elif self.high is None:
                self.high = (nibble, rs)
            else:
                high, mode = self.high
                self.high = None
                self.write((high << 4) | nibble, mode)
        self.enable = en

    def write(self, value, rs):
        if rs:
            if not self.cgram:
                self.ram[self.address & 127] = chr(value) if 32 <= value < 127 else '·'
                if self.entry_shift:
                    self.shift += self.increment
            self._move_address(self.increment)
        elif value == 1:
            self.ram = [' '] * 128
            self.address = self.shift = 0
            self.cgram = False
            self.increment = 1
        elif value & 0xFE == 2:
            self.address = self.shift = 0
            self.cgram = False
        elif value & 128:
            self.address = value & 127
            self.cgram = False
        elif value & 64:
            self.address = value & 63
            self.cgram = True
        elif value & 32:
            self.four_bit = not bool(value & 16)
            self.two_line = bool(value & 8)
        elif value & 16:
            if value & 8:
                self.shift += -1 if value & 4 else 1
            else:
                self._move_address(1 if value & 4 else -1)
        elif value & 8:
            self.display_on = bool(value & 4)
        elif value & 4:
            self.increment = 1 if value & 2 else -1
            self.entry_shift = bool(value & 1)

    def _move_address(self, direction):
        if self.cgram:
            self.address = (self.address + direction) & 63
        elif self.two_line:
            boundaries = {0x27: 0x40, 0x67: 0} if direction > 0 else {0x40: 0x27, 0: 0x67}
            self.address = boundaries.get(self.address, (self.address + direction) & 127)
        else:
            self.address = (self.address + direction) % 80

    def lines(self, powered=True):
        if not powered or not self.display_on:
            return [' ' * 16] * 2
        return [''.join(self.ram[(base + (i + self.shift) % 40) & 127] for i in range(16))
                for base in (0, 64)]


class SevenSegment:
    """Reconstruct the dominant held pattern, ignoring short inter-digit blanking.

    Active elapsed time ages live history. Instruction dwell distinguishes useful
    patterns from short blanking writes without counting Python MMIO overhead as
    firmware delay. Offline machines use instruction ticks for both quantities.
    """
    def __init__(self, window=300_000):
        self.window = window
        self.history = deque(maxlen=8192)
        self.last_tick = 0
        self.last_dwell_tick = 0
        self.last_digit = -1
        self.last_pattern = 0

    def observe(self, tick, digit, pattern, *, dwell_tick=None):
        self._record(tick, dwell_tick)
        self.last_digit, self.last_pattern = digit, pattern

    def _record(self, tick, dwell_tick=None):
        dwell_tick = tick if dwell_tick is None else dwell_tick
        if 0 <= self.last_digit < 4 and tick > self.last_tick:
            self.history.append((tick, self.last_digit, self.last_pattern,
                                 max(1, dwell_tick - self.last_dwell_tick)))
        self.last_tick = tick
        self.last_dwell_tick = dwell_tick
        while self.history and self.history[0][0] < tick - self.window:
            self.history.popleft()

    def patterns(self, tick, *, dwell_tick=None):
        self._record(tick, dwell_tick)
        weights = [{} for _ in range(4)]
        for _, d, p, duration in self.history:
            weights[d][p] = weights[d].get(p, 0) + duration
        return [max(w, key=w.get) if w else 0 for w in weights]
