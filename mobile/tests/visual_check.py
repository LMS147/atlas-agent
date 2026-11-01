import asyncio
import shutil
import sys
import functools
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else "visual-results").resolve()
async def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 origin=f'http://127.0.0.1:{server.server_port}' 
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
  for width,height in [(390,844),(1440,1000),(320,700)]:
   page=await browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
   for name in ['setup','chat','conversation','settings']:
    await page.goto(f'{origin}/{name}.html')
    await page.screenshot(path=str(ROOT/f'{name}-{width}.png'),full_page=True)
    problems=await page.evaluate('''() => ({overflow:document.documentElement.scrollWidth>innerWidth,controls:[...document.querySelectorAll('input,button,textarea,select')].filter(e=>e.getBoundingClientRect().width>0&&e.getBoundingClientRect().right>innerWidth+1).map(e=>e.outerHTML.slice(0,100))})''')
    print(name,width,problems)
    assert not problems['overflow'], f'{name} at {width}px overflows the viewport'
    assert not problems['controls'] or name!='setup', f'Setup controls clipped at {width}px'
   await page.close()
  page=await browser.new_page(viewport={'width':390,'height':600})
  errors=[]
  page.on('pageerror',lambda error: errors.append(str(error)))
  await page.goto(f'{origin}/3d.html')
  await page.wait_for_selector('[data-atlas-ready="true"]')
  await page.wait_for_timeout(1800)
  diagnostics=await page.evaluate('atlas.getDiagnostics()')
  assert diagnostics['frames']>0 and diagnostics['triangles']>0, diagnostics
  await page.screenshot(path=str(ROOT/'atlas-3d-idle.png'))
  await page.evaluate("atlas.setState('speaking',true)")
  await page.wait_for_timeout(400)
  assert await page.evaluate("atlas.getDiagnostics().mode")=='speaking'
  await page.screenshot(path=str(ROOT/'atlas-3d-speaking.png'))
  await page.evaluate('atlas.setPortrait(true)')
  await page.wait_for_timeout(350)
  await page.screenshot(path=str(ROOT/'atlas-3d-portrait.png'))
  await page.evaluate('atlas.setPortrait(false)')
  await page.evaluate('atlas.wave()')
  await page.wait_for_timeout(700)
  await page.screenshot(path=str(ROOT/'atlas-3d-wave.png'))
  await page.evaluate("atlas.setState('idle',false)")
  before=await page.evaluate('atlas.getDiagnostics().frames')
  await page.wait_for_timeout(350)
  assert before==await page.evaluate('atlas.getDiagnostics().frames')
  await page.evaluate('atlas.dispose()')
  assert not errors, errors
  print('PASS: 3D geometry rendered, speech state, waving, background pause, disposal',diagnostics)
  await browser.close()
 server.shutdown()
asyncio.run(main())
