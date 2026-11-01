import asyncio
import shutil
import sys
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else "visual-results").resolve()
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
  for width,height in [(390,844),(1440,1000),(320,700)]:
   page=await browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
   for name in ['setup','chat','conversation','settings']:
    await page.goto((ROOT/f'{name}.html').as_uri())
    await page.screenshot(path=str(ROOT/f'{name}-{width}.png'),full_page=True)
    problems=await page.evaluate('''() => ({overflow:document.documentElement.scrollWidth>innerWidth,controls:[...document.querySelectorAll('input,button,textarea,select')].filter(e=>e.getBoundingClientRect().width>0&&e.getBoundingClientRect().right>innerWidth+1).map(e=>e.outerHTML.slice(0,100))})''')
    print(name,width,problems)
    assert not problems['overflow'], f'{name} at {width}px overflows the viewport'
    assert not problems['controls'] or name!='setup', f'Setup controls clipped at {width}px'
   await page.close()
  await browser.close()
asyncio.run(main())
