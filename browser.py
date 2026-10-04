"""Bounded interactions against an explicitly authorised test origin."""
from pathlib import Path
from policy import origin

SNAPSHOT='''() => {
 const nodes=[...document.querySelectorAll('a,button,input,textarea,select,[role="button"]')]
   .filter(e=>e.getClientRects().length && getComputedStyle(e).visibility!=='hidden');
 const controls=nodes.slice(0,100).map((e,id)=>({id,tag:e.tagName.toLowerCase(),type:e.type||'',
 label:(e.getAttribute('aria-label')||[...(e.labels||[])].map(x=>x.innerText).join(' ')||e.innerText||e.getAttribute('title')||'').trim().slice(0,200),
 placeholder:e.getAttribute('placeholder')||'',disabled:!!e.disabled,focused:e===document.activeElement,
 value:e.type==='password'?'[excluded]':String(e.value||'').slice(0,100),
 options:e.tagName==='SELECT'?[...e.options].map(o=>({value:o.value,label:o.text})):[]}));
 return {text:document.body.innerText.slice(0,12000),controls,
 overflow:document.documentElement.scrollWidth>innerWidth+2,
 alerts:[...document.querySelectorAll('[role="alert"],.error-message')].filter(e=>e.getClientRects().length).map(e=>e.innerText.slice(0,500))};
}'''

class Session:
    def __init__(self,browser,url,profile):
        self.allowed=origin(url);self.network=[]
        self.context=browser.new_context(viewport=profile['viewport'],accept_downloads=False,service_workers='block')
        self.context.route('**/*',self._route)
        self.context.route_web_socket('**/*',lambda ws:ws.close())
        self.page=self.context.new_page();self.page.set_default_timeout(5000)
        self.page.on('dialog',lambda d:d.dismiss())
        self.context.on('page',lambda p:p.close() if p!=self.page else None)
    def _route(self,route):
        try: allowed=origin(route.request.url)==self.allowed
        except ValueError: allowed=False
        if allowed: route.continue_()
        else:
            self.network.append('Blocked an off-origin request')
            route.abort()
    def start(self,url):
        self.page.goto(url,wait_until='domcontentloaded',timeout=15000)
    def observe(self): return self.page.evaluate(SNAPSHOT)
    def screenshot(self,path): self.page.screenshot(path=str(path),full_page=False,timeout=5000)
    def success(self,marker): return self.page.get_by_text(marker,exact=True).filter(visible=True).count()>0
    def act(self,action,data,keyboard_only):
        kind=action['action']
        if kind=='key': self.page.keyboard.press(action['key']);return
        # Rebuild from current visible elements and compare the observation before acting in runner.
        nodes=self.page.locator('a,button,input,textarea,select,[role="button"]').all()
        visible=[e for e in nodes if e.is_visible()]
        target=visible[action['target']]
        if keyboard_only and not target.evaluate('(e)=>e===document.activeElement'):
            raise ValueError('Keyboard profile must focus the field using Tab before editing.')
        if kind=='click': target.click()
        elif kind=='fill': target.fill(data[action['data_key']])
        elif kind=='select': target.select_option(data[action['data_key']])
    def settle(self):
        self.page.wait_for_timeout(150)
    def close(self): self.context.close()
