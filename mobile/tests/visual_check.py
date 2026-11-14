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
  browser=await p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
  for width,height in [(360,800),(390,844),(768,1024),(1440,1000),(320,700)]:
   page=await browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
   for name in ['setup','setup-loading','setup-error','chat','conversation','cached-chat','memory-empty','memory','companion','files','tools','profile','settings','drawer']:
    await page.goto(f'{origin}/{name}.html')
    await page.screenshot(path=str(ROOT/f'{name}-{width}.png'),full_page=True,animations='disabled')
    problems=await page.evaluate('''() => ({overflow:document.documentElement.scrollWidth>innerWidth,controls:[...document.querySelectorAll('input,button,textarea,select')].filter(e=>e.getBoundingClientRect().width>0&&e.getBoundingClientRect().right>innerWidth+1).map(e=>e.outerHTML.slice(0,100))})''')
    print(name,width,problems)
    if not name.startswith('setup'):
     nav=page.locator('.bottom-navigation')
     assert await nav.locator('button').count()==5
     box=await nav.bounding_box()
     assert abs(box['y']+box['height']-height)<2, (name,width,box)
    if name=='drawer':
     assert await page.locator('[role="dialog"][aria-label="Workspace menu"]').is_visible()
     drawer_box=await page.locator('.workspace-drawer').bounding_box()
     assert abs(drawer_box['x'])<1, drawer_box
     assert await page.locator('.drawer-navigation button').count()==7
     assert await page.locator('.drawer-navigation .active strong').inner_text()=='Connection settings'
     assert await page.locator('main').get_attribute('inert') is not None
     await page.evaluate("""async()=>{
      const navigation=await import('./_content/Atlas.UI/atlas-navigation.js');
      navigation.openDrawer(document.querySelector('.workspace-drawer'),{invokeMethodAsync:async()=>{
       document.querySelectorAll('[inert]').forEach(e=>e.removeAttribute('inert'));
       document.querySelector('.workspace-drawer').remove();document.querySelector('.drawer-backdrop').remove();
       navigation.closeDrawer();window.drawerClosed=true;
      }},'workspace-more-button');
     }""")
     for _ in range(11):
      await page.keyboard.press('Tab')
      assert await page.evaluate("document.querySelector('.workspace-drawer').contains(document.activeElement)")
     await page.keyboard.press('Shift+Tab')
     assert await page.evaluate("document.querySelector('.workspace-drawer').contains(document.activeElement)")
     await page.keyboard.press('Escape')
     await page.wait_for_function('window.drawerClosed===true')
     assert await page.evaluate("document.activeElement.id")=='workspace-more-button' 
    assert not problems['overflow'], f'{name} at {width}px overflows the viewport'
    assert not problems['controls'], f'Setup controls clipped at {width}px'
    if name=='companion':
     assert await page.locator('.orb-fallback:visible').count()==1
     assert await page.locator('.orb-stage canvas:visible').count()==0
     assert await page.locator('.orb-controls:visible').count()==0
    if name=='profile':
     assert await page.locator('.profile-document h1').inner_text()=='Atlas'
     assert await page.locator('.profile-document li').count()==3
    if name=='chat':
     assert await page.locator('.atlas-orb:visible').count()==1
    if name=='conversation':
     assert await page.locator('.atlas-orb:visible').count()==0
   # Text scaling and a resized viewport exercise layout, not a native keyboard.
   await page.goto(f'{origin}/files.html')
   await page.add_style_tag(content='body,button,input,textarea,select,small{font-size:20px!important}')
   assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   await page.screenshot(path=str(ROOT/f'files-large-text-{width}.png'),full_page=True)
   await page.goto(f'{origin}/conversation.html')
   await page.set_viewport_size({'width':width,'height':420})
   await page.evaluate("""async()=>{
    window.DotNet={createJSObjectReference:x=>x};
    const navigation=await import('./_content/Atlas.UI/atlas-navigation.js');
    window.layout=navigation.observeLayout();
    const input=document.querySelector('.composer textarea');input.value='A long editable message. '.repeat(80);input.dispatchEvent(new Event('input',{bubbles:true}));
    input.focus();window.scrollTo(0,document.body.scrollHeight);
   }""")
   await page.wait_for_timeout(100)
   assert await page.evaluate("""() => {
    const input=document.querySelector('.composer textarea'),composer=document.querySelector('.composer').getBoundingClientRect(),nav=document.querySelector('.bottom-navigation').getBoundingClientRect();
    return input.clientHeight<=162 && input.scrollHeight>input.clientHeight && composer.bottom<=nav.top+1;
   }""")
   await page.screenshot(path=str(ROOT/f'chat-reduced-height-{width}.png'),full_page=True)
   await page.evaluate('layout.dispose()')
   await page.close()
  page=await browser.new_page(viewport={'width':390,'height':600})
  errors=[]
  page.on('pageerror',lambda error: errors.append(str(error)))
  await page.goto(f'{origin}/orb.html')
  await page.wait_for_selector('[data-orb-ready="true"]')
  await page.wait_for_timeout(1200)
  diagnostics=await page.evaluate('atlas.getDiagnostics()')
  assert diagnostics['frames']>0 and diagnostics['particles']>0, diagnostics
  for mode in ['idle','thinking','speaking','disconnected','error']:
   await page.evaluate("mode=>{atlas.setState(mode,true);document.getElementById('status').textContent=mode;}",mode)
   await page.wait_for_timeout(500)
   assert await page.evaluate('atlas.getDiagnostics().state')==mode
   await page.screenshot(path=str(ROOT/f'atlas-orb-{mode}.png'))
  await page.evaluate("atlas.setState('idle',false)")
  before=await page.evaluate('atlas.getDiagnostics().frames')
  await page.wait_for_timeout(300)
  assert before==await page.evaluate('atlas.getDiagnostics().frames')
  await page.evaluate("atlas.setState('idle',true)")
  await page.wait_for_timeout(300)
  assert before<await page.evaluate('atlas.getDiagnostics().frames')
  await page.emulate_media(reduced_motion='reduce')
  await page.wait_for_timeout(1200)
  before=await page.evaluate('atlas.getDiagnostics().orbitTime')
  await page.wait_for_timeout(300)
  assert before==await page.evaluate('atlas.getDiagnostics().orbitTime')
  await page.evaluate("document.getElementById('canvas').dispatchEvent(new Event('contextlost',{cancelable:true}))")
  assert await page.locator('#fallback:visible').count()==1
  assert await page.locator('#canvas:visible').count()==0
  await page.screenshot(path=str(ROOT/'atlas-orb-fallback.png'))
  await page.evaluate('atlas.dispose()')
  assert not errors, errors
  print('PASS: particle orb rendering, states, pause/resume, reduced motion, fallback and disposal',diagnostics)
  await browser.close()
 server.shutdown()
asyncio.run(main())
