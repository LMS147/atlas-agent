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
from android_smoke_diagnostics import collect_diagnostics

OUT = pathlib.Path('android-smoke-results')
OUT.mkdir(exist_ok=True)
PACKAGE = 'com.atlas.ai.hybrid'


def adb(*args):
    return subprocess.check_output(['adb', *args], text=True, timeout=20, stderr=subprocess.STDOUT).strip()


class DeviceDisconnected(RuntimeError):
    pass


def checkpoint(name):
    print(f'CHECKPOINT: {name}', flush=True)
    (OUT/'checkpoint.txt').write_text(name, encoding='utf-8')


def until(action, seconds=45):
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        try:
            result = action()
            if result:
                return result
        except DeviceDisconnected:
            raise
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
        try:
            self.sequence += 1
            self.socket.send(json.dumps(dict(id=self.sequence, method=method, params=params or {})))
            while True:
                raw = self.socket.recv()
                if not raw:
                    raise DeviceDisconnected('Android WebView disconnected; see live-logcat and host diagnostics.')
                message = json.loads(raw)
                if message.get('id') == self.sequence:
                    assert 'error' not in message, message
                    return message.get('result', {})
                self.events.append(message)
        except (websocket.WebSocketConnectionClosedException, ConnectionError, OSError) as error:
            raise DeviceDisconnected('Android WebView connection was lost; see live-logcat and host diagnostics.') from error

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate', dict(expression=expression, returnByValue=True))
        assert 'exceptionDetails' not in result, result
        return result['result'].get('value')


cdp = None
live_logcat = None
live_output = None
original_motion_scale = None
try:
    original_motion_scale = adb('shell', 'settings', 'get', 'global', 'animator_duration_scale')
    adb('shell', 'settings', 'put', 'global', 'animator_duration_scale', '1')
    adb('logcat', '-c')
    live_output = (OUT/'live-logcat.txt').open('wb')
    live_logcat = subprocess.Popen(['adb', 'logcat', '-v', 'threadtime'], stdout=live_output, stderr=subprocess.STDOUT)
    checkpoint('Launching installed Atlas APK')
    adb('shell', 'monkey', '-p', PACKAGE, '-c', 'android.intent.category.LAUNCHER', '1')
    pid = until(lambda: adb('shell', 'pidof', PACKAGE))
    adb('forward', 'tcp:9222', f'localabstract:webview_devtools_remote_{pid}')

    def target():
        with urllib.request.urlopen('http://localhost:9222/json/list', timeout=3) as response:
            return next((t for t in json.load(response) if t.get('type') == 'page'), None)

    cdp = CDP(until(target)['webSocketDebuggerUrl'])
    until(lambda: cdp.evaluate("!!document.querySelector('#token:not(:disabled)')"))
    # Obtain native WebView offset (status bar is outside the DOM viewport).
    def webview_origin():
        adb('shell', 'uiautomator', 'dump', '/sdcard/window.xml')
        tree = ET.fromstring(adb('shell', 'cat', '/sdcard/window.xml'))
        view = next(n for n in tree.iter('node') if n.get('class') == 'android.webkit.WebView')
        left, top, _, _ = map(int, re.findall(r'\d+', view.attrib['bounds']))
        return left, top
    left, top = until(webview_origin, 60)
    checkpoint('Setup ready; opening orb preview')
    (OUT/'before-orb.html').write_text(str(cdp.evaluate('document.documentElement.outerHTML')), encoding='utf-8')
    # Exercise the bundled particle orb through Blazor before any server login.
    cdp.evaluate("""(()=>{
        window.orbDrawFrames=0;window.orbErrors=[];
        const fillRect=CanvasRenderingContext2D.prototype.fillRect;
        CanvasRenderingContext2D.prototype.fillRect=function(...args){
            if(this.canvas.classList.contains('orb-canvas') && args[0]===0 && args[1]===0)window.orbDrawFrames++;
            return fillRect.apply(this,args);
        };
    })()""")
    cdp.evaluate("document.querySelector('.meet-atlas').click()")
    until(lambda: cdp.evaluate("!!document.querySelector('.companion-dialog')"))
    checkpoint('Orb preview opened; waiting for renderer or fallback')
    until(lambda: cdp.evaluate("!!document.querySelector('[data-orb-ready=\"true\"] canvas:not([hidden])') || document.body.innerText.includes(\"Orb display details\")"), 45)
    print('Atlas native particle orb ready:', cdp.evaluate("!!document.querySelector('[data-orb-ready=\"true\"] canvas:not([hidden])')"))
    animated=cdp.evaluate("!!document.querySelector('[data-orb-ready=\"true\"] canvas:not([hidden])')")
    checkpoint('Verifying continuously animated orb without a server connection')
    # The main Android proof requires the actual animated canvas, not fallback.
    assert animated, 'Live-orb acceptance requires an animated canvas on this emulator'
    until(lambda: cdp.evaluate("!matchMedia('(prefers-reduced-motion: reduce)').matches"), 10)
    until(lambda: cdp.evaluate('window.orbDrawFrames>3'))
    assert cdp.evaluate("document.querySelector('.atlas-orb').dataset.presence==='disconnected'"), 'Expected an offline, locally rendered orb'
    proof={'state':'disconnected','source':'installed Android APK; bundled Canvas renderer','recording':'atlas-orb-live-android.mp4'}
    before=cdp.evaluate('window.orbDrawFrames')
    pixels_before=cdp.evaluate("document.querySelector('.orb-canvas').toDataURL()")
    # ADB records the actual Android screen; no generated/synthetic video.
    remote='/sdcard/atlas-orb-live-android.mp4'
    subprocess.run(['adb','shell','screenrecord','--time-limit','10','--size','720x1280','--bit-rate','2000000',remote],check=True,timeout=25)
    adb('pull',remote,str(OUT/'atlas-orb-live-android.mp4'))
    after=cdp.evaluate('window.orbDrawFrames')
    pixels_after=cdp.evaluate("document.querySelector('.orb-canvas').toDataURL()")
    assert after-before>=30, f'Insufficient orb drawing during recording: {after-before}'
    assert pixels_before!=pixels_after, 'The orb pixels did not change during the recording'
    proof['rendered_frames_during_recording']=after-before
    proof['pixels_changed']=True
    with (OUT/'atlas-orb-live-android.png').open('wb') as screen:
        subprocess.run(['adb','exec-out','screencap','-p'],stdout=screen,check=True,timeout=15)
    print(f'PASS: live disconnected orb; {after-before} rendered frames during 10-second Android recording',flush=True)

    checkpoint('Checking reduced-motion preference')
    adb('shell','settings','put','global','animator_duration_scale','0')
    until(lambda: cdp.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"),10)
    time.sleep(2)
    frozen=cdp.evaluate('window.orbDrawFrames');time.sleep(1)
    assert frozen==cdp.evaluate('window.orbDrawFrames'), 'Reduced motion did not settle to a static orb'
    proof['reduced_motion_stops_drawing']=True
    adb('shell','settings','put','global','animator_duration_scale','1')
    until(lambda: cdp.evaluate(f'window.orbDrawFrames>{frozen}'),10)

    checkpoint('Checking actual orb drawing pauses in background')
    adb('shell','input','keyevent','3')
    until(lambda: cdp.evaluate('document.hidden'),10)
    time.sleep(1)
    paused=cdp.evaluate('window.orbDrawFrames');time.sleep(1)
    assert paused==cdp.evaluate('window.orbDrawFrames'), 'Orb kept drawing in background'
    proof['background_pauses_drawing']=True
    adb('shell','monkey','-p',PACKAGE,'-c','android.intent.category.LAUNCHER','1')
    until(lambda: cdp.evaluate(f'!document.hidden && window.orbDrawFrames>{paused}'))
    proof['resume_restarts_drawing']=True
    cdp.evaluate("document.querySelector('[aria-label=\"Close Atlas preview\"]').click()")
    until(lambda: cdp.evaluate("!document.querySelector('.companion-dialog')"))
    time.sleep(.5)
    closed=cdp.evaluate('window.orbDrawFrames');time.sleep(1)
    assert closed==cdp.evaluate('window.orbDrawFrames'), 'Disposed orb kept drawing'
    proof['closing_view_stops_drawing']=True
    (OUT/'orb-live-verification.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    adb('shell','settings','put','global','animator_duration_scale',original_motion_scale)
    print('PASS: reduced motion, background pause, resume and view disposal',flush=True)

    def tap(selector):
        # Scrolling is only to position a control; input/click events come from ADB touches.
        cdp.evaluate(f'document.querySelector({json.dumps(selector)}).scrollIntoView({{block:"center"}})')
        time.sleep(.3)
        x, y = cdp.evaluate(f'''(()=>{{const r=document.querySelector({json.dumps(selector)}).getBoundingClientRect();return [(r.x+r.width/2)*devicePixelRatio,(r.y+r.height/2)*devicePixelRatio]}})()''')
        adb('shell', 'input', 'tap', str(round(left+x)), str(round(top+y)))
        time.sleep(.3)

    checkpoint('Orb preview closed; checking native input and connection recovery')
    tap('#server')
    adb('shell', 'input', 'keyevent', '123')
    adb('shell', 'input', 'keyevent', *(['67'] * 100))
    adb('shell', 'input', 'text', 'https://127.0.0.1:1/')
    assert cdp.evaluate("document.querySelector('#server').value") == 'https://127.0.0.1:1/'
    adb('shell', 'input', 'keyevent', '4')  # hide URL keyboard before locating the next field
    time.sleep(.5)
    tap('#token')
    until(lambda: cdp.evaluate("document.activeElement.id === 'token'"), 10)
    # A newly opened password IME replaces its input connection asynchronously.
    # Wait for that transition and type at human speed rather than flooding key events.
    time.sleep(1)
    for character in 'atlas-emulator-fake-token-1234567890':
        adb('shell', 'input', 'text', character)
        time.sleep(.08)
    until(lambda: cdp.evaluate("document.querySelector('#token').value") == 'atlas-emulator-fake-token-1234567890', 10)
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
    if original_motion_scale is not None:
        try:
            adb('shell','settings','put','global','animator_duration_scale',original_motion_scale)
        except Exception:
            pass
    if live_logcat is not None:
        try:
            live_logcat.terminate()
            try:
                live_logcat.wait(timeout=5)
            except subprocess.TimeoutExpired:
                live_logcat.kill()
                live_logcat.wait(timeout=5)
        except Exception:
            pass
    if live_output is not None:
        try:
            live_output.close()
        except Exception:
            pass
    collect_diagnostics(OUT, cdp)
    if cdp is not None:
        try:
            cdp.socket.close()
        except Exception:
            pass
