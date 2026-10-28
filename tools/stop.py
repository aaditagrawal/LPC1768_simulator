"""Stop only a server started by this workspace's launcher."""
from pathlib import Path
import os
import signal

ROOT=Path(__file__).resolve().parents[1]
pidfile=ROOT/'build/server.pid'
if not pidfile.exists():
    raise SystemExit('No launcher PID recorded. If running in a terminal, press Ctrl+C there.')
pid=int(pidfile.read_text())
try:
    import ctypes
    # Verify the recorded PID still names this workspace's Python server before
    # asking Windows to terminate it. A stale/reused PID must not kill other work.
    if os.name=='nt':
        import subprocess
        script='(Get-CimInstance Win32_Process -Filter "ProcessId = '+str(pid)+'").CommandLine'
        cmd=subprocess.run(['powershell','-NoProfile','-Command',script],capture_output=True,text=True).stdout
        if 'simulator.server' not in cmd or str(ROOT).lower() not in cmd.lower():
            raise SystemExit('Recorded PID does not match this workspace server. Nothing stopped.')
    os.kill(pid,signal.SIGTERM)
    print('Local simulator server stopped.')
except ProcessLookupError:
    print('Local simulator server is already stopped.')
pidfile.unlink(missing_ok=True)
