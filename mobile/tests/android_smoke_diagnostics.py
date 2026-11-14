"""Best-effort evidence collection: never replace the smoke test's original error."""
import json
import subprocess
from pathlib import Path


def collect_diagnostics(output, cdp=None, run=subprocess.run):
    output = Path(output)
    errors = []

    def capture(name, action):
        try:
            data = action()
            path = output / name
            if isinstance(data, bytes):
                path.write_bytes(data)
            else:
                path.write_text(str(data), encoding='utf-8')
        except Exception as error:
            errors.append({'artifact': name, 'error': str(error)})

    def command(args, binary=False):
        result = run(args, capture_output=True, timeout=15, check=False)
        if result.returncode:
            raise RuntimeError(f'{args}: exit {result.returncode}; {result.stderr.decode(errors="replace")}')
        return result.stdout if binary else result.stdout.decode(errors='replace')

    try:
        output.mkdir(parents=True, exist_ok=True)
        if cdp is not None:
            capture('webview-events.json', lambda: json.dumps(cdp.events, indent=2))
            capture('page.txt', lambda: cdp.evaluate('document.body.innerText'))
            capture('page.html', lambda: cdp.evaluate('document.documentElement.outerHTML'))
            capture('input-state.json', lambda: json.dumps(cdp.evaluate("({focus:document.activeElement.id,tokenLength:document.querySelector('#token')?.value.length,server:document.querySelector('#server')?.value})")))
        # Each item runs even if the WebView socket or emulator has disappeared.
        capture('adb-devices.txt', lambda: command(['adb', 'devices', '-l']))
        capture('adb-state.txt', lambda: command(['adb', 'get-state']))
        capture('logcat.txt', lambda: command(['adb', 'logcat', '-d']))
        capture('screen.png', lambda: command(['adb', 'exec-out', 'screencap', '-p'], binary=True))
        capture('host-memory.txt', lambda: command(['free', '-m']))
        capture('host-processes.txt', lambda: command(['ps', '-eo', 'pid,ppid,rss,args']))
        capture('host-kernel.txt', lambda: command(['sudo', '-n', 'dmesg', '--ctime']))
        capture('diagnostic-errors.json', lambda: json.dumps(errors, indent=2))
    except Exception:
        # Even a full/unwritable artifact directory must not mask the test failure.
        pass
    return errors
