"""Visual design fixtures; production tournament renderer, no gameplay claims."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
URL=os.environ.get('BACKENBEBEN_UI_PREVIEW','http://localhost:8920/docs/ui-preview/tournament.html')

async def main():
 errors=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),headless=True)
  p=await browser.new_page(viewport={'width':1600,'height':1000})
  p.on('pageerror',lambda e:errors.append(str(e)))
  p.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  await p.goto(URL);await p.wait_for_selector('.entrantList li')
  assert await p.locator('.entrantList li').count()==8
  assert await p.locator('#tournamentChampion').is_hidden()
  await p.screenshot(path=str(ROOT/'logs/ui-design-lobby.png'))
  await p.locator('#tournamentCopy').click();await p.wait_for_function('document.querySelector("#toast").textContent.includes("kopiert")');await p.wait_for_function('getComputedStyle(document.querySelector("#toast")).opacity==="0"')
  await p.locator('[data-preview=running]').click();await p.wait_for_timeout(250)
  assert await p.locator('.bracketRound').count()==3
  assert await p.locator('#tournamentFocus').is_visible()
  await p.screenshot(path=str(ROOT/'logs/ui-design-bracket.png'))
  await p.locator('[data-preview=finished]').click()
  assert await p.locator('#tournamentChampion').is_visible()
  assert await p.locator('#tournamentChampionName').text_content()=='SVEN'
  await p.screenshot(path=str(ROOT/'logs/ui-design-champion.png'))
  await p.locator('#previewCount').select_option('20');await p.locator('[data-preview=waiting]').click()
  assert await p.locator('.entrantList li').count()==20
  await p.screenshot(path=str(ROOT/'logs/ui-design-20.png'))
  await p.locator('[data-preview=running]').click();await p.wait_for_timeout(300)
  assert await p.locator('.bracketRound').count()==5
  await p.locator('#tournamentBracket').evaluate('(el)=>{el.scrollTo({left:250,top:400,behavior:"instant"})}')
  before=await p.locator('#tournamentBracket').evaluate('(e)=>[e.scrollLeft,e.scrollTop]')
  await p.locator('[data-preview=running]').click();await p.wait_for_timeout(100)
  after=await p.locator('#tournamentBracket').evaluate('(e)=>[e.scrollLeft,e.scrollTop]');assert before==after,(before,after)
  await p.locator('#tournamentFocus').click();await p.wait_for_timeout(800)
  own=p.locator('.bracketMatch[data-own=true]').last
  b=await own.bounding_box();container=await p.locator('#tournamentBracket').bounding_box()
  assert b['x']>=container['x'] and b['x']+b['width']<=container['x']+container['width']+1
  await p.locator('[data-preview=cancelled]').click()
  assert not any(t=='KAMPF LÄUFT' for t in await p.locator('.bracketMatch small').all_text_contents())
  for width in (1280,850,390):
   await p.set_viewport_size({'width':width,'height':844})
   for stage in ('waiting','running','finished'):
    await p.locator('[data-preview='+stage+']').click();await p.wait_for_timeout(150)
    assert await p.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,stage)
    assert await p.locator('#tournamentPanel').is_visible()
   if width==390:await p.screenshot(path=str(ROOT/'logs/ui-design-mobile.png'))
  assert not errors,errors
  await browser.close()
 report=dict(errors=errors,fixture_only=True,widths=[1600,1280,850,390],stages=4,entrants=[8,20],copy=True,focus=True,scroll_preserved=True)
 (ROOT/'logs/ui-design-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)

if __name__=='__main__':asyncio.run(main())
