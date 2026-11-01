"""Exercise real Android touches, using CDP only to observe the bundled WebView.
No backend credentials or external inference calls: connection intentionally fails locally.
"""
import json
import pathlib
import re
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
import websocket

OUT = pathlib.Path('android-smoke-results')
OUT.mkdir(exist_ok=True)
PACKAGE = 'com.atlas.ai.hybrid'


def adb(*args):
    return subprocess.check_output(['adb', *args], text=True).strip()


def until(action, seconds=45):
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        try:
            result = action()
            if result:
                return result
        except Exception as error:
            last = error
        time.sleep(.5)
    raise AssertionError(f'Timed out waiting for UI: {last}')


class CDP:
    def __init__(self, url):
        self.socket = websocket.create_connection(url, timeout=10, suppress_origin=True)
        self.sequence = 0
        self.events = []
        self.call('Runtime.enable')

    def call(self, method, params=None):
        self.sequence += 1
        self.socket.send(json.dumps(dict(id=self.sequence, method=method, params=params or {})))
        while True:
            message = json.loads(self.socket.recv())
            if message.get('id') == self.sequence:
                assert 'error' not in message, message
                return message.get('result', {})
            self.events.append(message)

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate', dict(expression=expression, returnByValue=True))
        assert 'exceptionDetails' not in result, result
        return result['result'].get('value')


cdp = None
try:
    adb('logcat', '-c')
    adb('shell', 'monkey', '-p', PACKAGE, '-c', 'android.intent.category.LAUNCHER', '1')
    pid = until(lambda: adb('shell', 'pidof', PACKAGE))
    adb('forward', 'tcp:9222', f'localabstract:webview_devtools_remote_{pid}')

    def target():
        with urllib.request.urlopen('http://localhost:9222/json/list', timeout=3) as response:
            return next((t for t in json.load(response) if t.get('type') == 'page'), None)

    cdp = CDP(until(target)['webSocketDebuggerUrl'])
    until(lambda: cdp.evaluate("!!document.querySelector('#token:not(:disabled)')"))
    # Obtain native WebView offset (status bar is outside the DOM viewport).
    adb('shell', 'uiautomator', 'dump', '/sdcard/window.xml')
    tree = ET.fromstring(adb('shell', 'cat', '/sdcard/window.xml'))
    view = next(n for n in tree.iter('node') if n.get('class') == 'android.webkit.WebView')
    left, top, _, _ = map(int, re.findall(r'\d+', view.attrib['bounds']))

    def tap(selector):
        # Scrolling is only to position a control; input/click events come from ADB touches.
        cdp.evaluate(f'document.querySelector({json.dumps(selector)}).scrollIntoView({{block:"center"}})')
        time.sleep(.3)
        x, y = cdp.evaluate(f'''(()=>{{const r=document.querySelector({json.dumps(selector)}).getBoundingClientRect();return [(r.x+r.width/2)*devicePixelRatio,(r.y+r.height/2)*devicePixelRatio]}})()''')
        adb('shell', 'input', 'tap', str(round(left+x)), str(round(top+y)))
        time.sleep(.3)

    tap('#server')
    adb('shell', 'input', 'keyevent', '123')
    adb('shell', 'input', 'keyevent', *(['67'] * 100))
    adb('shell', 'input', 'text', 'https://127.0.0.1:1/')
    assert cdp.evaluate("document.querySelector('#server').value") == 'https://127.0.0.1:1/'
    tap('#token')
    adb('shell', 'input', 'text', 'atlas-emulator-fake-token-1234567890')
    # Before blur, oninput must enable Connect. This catches the setup-screen regression.
    until(lambda: cdp.evaluate("!document.querySelector('button.primary').disabled"), 10)
    adb('shell', 'input', 'keyevent', '4')  # dismiss keyboard
    tap('button.primary')
    until(lambda: cdp.evaluate("!!document.querySelector('.alert.error')"), 30)
    assert cdp.evaluate("!document.querySelector('button.primary').disabled"), 'UI stayed busy after connection failed'
    before = cdp.evaluate("document.querySelector('input[type=checkbox]').checked")
    tap('input[type=checkbox]')
    until(lambda: cdp.evaluate("document.querySelector('input[type=checkbox]').checked") != before, 10)
    print('PASS: native text input, Connect callback/error recovery, and checkbox touch')
finally:
    if cdp:
        (OUT/'webview-events.json').write_text(json.dumps(cdp.events, indent=2))
        (OUT/'page.txt').write_text(str(cdp.evaluate('document.body.innerText')))
    (OUT/'logcat.txt').write_text(adb('logcat', '-d'))
    with (OUT/'screen.png').open('wb') as screenshot:
        subprocess.run(['adb', 'exec-out', 'screencap', '-p'], stdout=screenshot, check=False)
