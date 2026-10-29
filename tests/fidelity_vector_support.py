"""Buffered per-vector evidence; test-only, independent of simulation code."""
import hashlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def vector_log(request):
    records = []
    digests = {}

    def record(machine, identity, expected, observed, inputs, lab, evidence):
        key = id(machine)
        if key not in digests:
            digests[key] = hashlib.sha256(machine.hex_text.encode()).hexdigest()
        entry = {
            'id': request.node.nodeid + '/' + identity,
            'lab': lab,
            'firmware_sha256': digests[key],
            'initial_registers': getattr(machine, '_audit_initial', {}),
            'initial_gpio': getattr(machine, '_audit_initial_gpio', None),
            'hardware': {'cables': [c[:] for c in machine.board.cables],
                         'jumpers': dict(machine.board.jumpers)},
            'events': inputs,
            'ticks': machine.ticks,
            'expected': expected,
            'observed': observed,
            'status': 'PASS' if expected == observed else 'FAIL',
            'evidence': evidence,
            'confidence': 'Document-backed ideal digital behavior; no real-board measurement',
        }
        if expected != observed:
            entry['gpio'] = [vars(g).copy() for g in machine.gpio]
            entry['mmio_trace'] = list(getattr(machine, '_audit_trace', []))
        records.append(entry)

    yield record
    target = Path('build/hardware-audit/display-vectors.jsonl')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('a', encoding='utf-8') as output:
        for entry in records:
            output.write(json.dumps(entry, ensure_ascii=False) + '\n')
