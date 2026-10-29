r"""Run reproducible backend/build/browser checks on an isolated local service.

Usage: .venv\Scripts\python.exe tools/run_hardware_audit.py [--backend-only]
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/hardware-audit'


def totals(path):
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == 'testsuite' else list(root.iter('testsuite'))
    return {key: sum(int(s.get(key, 0)) for s in suites)
            for key in ('tests', 'failures', 'errors', 'skipped')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend-only', action='store_true')
    parser.add_argument('--port', type=int, default=8886)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    os.chdir(ROOT)
    # These are this runner's own generated ledgers, never source files.
    for name in ['cases.jsonl', 'display-vectors.jsonl']:
        (OUT / name).write_text('', encoding='utf-8')
    (ROOT / 'build/audit-adc-cases.jsonl').write_text('', encoding='utf-8')
    metadata = {'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'python': sys.version, 'baseline_commit': subprocess.check_output(
                    ['git', 'rev-parse', 'HEAD'], text=True).strip(), 'sources': {}}
    for name in ['ESD.pdf', 'ARM_LPC-1768_User_Manual (1).pdf']:
        metadata['sources'][name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()

    def run(command, label, env=None):
        print(f'Running {label}', flush=True)
        started = time.perf_counter()
        with (OUT / (label + '.log')).open('w', encoding='utf-8') as log:
            result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        metadata[label] = {'command': command, 'exit_code': result.returncode,
                           'seconds': round(time.perf_counter() - started, 3)}
        print(f'{label}: exit {result.returncode}', flush=True)
        return result.returncode

    backend = run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                   '--junitxml=build/hardware-audit/backend.xml'], 'backend')
    metadata['backend']['totals'] = totals(OUT / 'backend.xml')
    status = backend
    if not args.backend_only:
        npm = 'npm.cmd' if os.name == 'nt' else 'npm'
        status |= run([npm, 'run', 'build'], 'build')
        with socket.socket() as check:
            check.bind(('127.0.0.1', args.port))
        env = dict(os.environ, LPC_LAB_PORT=str(args.port),
                   LPC_LAB_URL=f'http://127.0.0.1:{args.port}',
                   PLAYWRIGHT_JUNIT_OUTPUT_NAME=str(OUT / 'browser.xml'))
        with (OUT / 'server.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen([sys.executable, '-m', 'simulator.server'],
                                       env=env, stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                deadline = time.monotonic() + 15
                while True:
                    try:
                        with urllib.request.urlopen(env['LPC_LAB_URL'] + '/api/info', timeout=1):
                            break
                    except OSError:
                        if process.poll() is not None or time.monotonic() >= deadline:
                            raise RuntimeError('Isolated audit server did not start')
                        time.sleep(.1)
                status |= run([npm, 'run', 'test:browser', '--', '--reporter=line,junit',
                               '--output=test-results/hardware-audit'], 'browser', env)
                metadata['browser']['totals'] = totals(OUT / 'browser.xml')
            finally:
                process.terminate()
                process.wait(timeout=10)
    metadata['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    metadata['exit_code'] = status
    (OUT / 'summary.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps(metadata, indent=2), flush=True)
    return status


if __name__ == '__main__':
    raise SystemExit(main())
