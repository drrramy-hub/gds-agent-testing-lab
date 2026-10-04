"""Boundaries for a local test harness, not a sandbox for hostile websites."""
import json
from urllib.parse import urlsplit

def origin(url):
    u=urlsplit(url)
    if u.scheme not in ('http','https') or not u.hostname or u.username or u.password:
        raise ValueError('Use an HTTP(S) URL without embedded credentials.')
    port=u.port or (443 if u.scheme=='https' else 80)
    return (u.scheme,u.hostname.lower(),port)

def validate_config(c):
    if not isinstance(c,dict): raise ValueError('Configuration must be an object.')
    origin(c.get('url',''))
    for key in ('task','success_text'):
        if not isinstance(c.get(key),str) or not 3<=len(c[key])<=3000: raise ValueError('Set task and success_text.')
    data=c.get('test_data')
    if not isinstance(data,dict) or not 1<=len(data)<=20: raise ValueError('Supply synthetic test_data.')
    for k,v in data.items():
        if not isinstance(k,str) or not k or not isinstance(v,str) or len(v)>500: raise ValueError('Invalid test data.')
    if type(c.get('max_steps',16)) is not int or not 1<=c.get('max_steps',16)<=30: raise ValueError('max_steps must be 1–30.')
    if type(c.get('max_seconds',300)) is not int or not 10<=c.get('max_seconds',300)<=600: raise ValueError('max_seconds must be 10–600.')
    return c

def validate_action(a,controls,profile,data):
    if not isinstance(a,dict) or set(a)-{'action','target','data_key','key','reason'}:
        raise ValueError('Invalid action structure.')
    kind=a.get('action')
    if kind not in ('click','fill','select','key','stop'): raise ValueError('Action not allowed.')
    if not isinstance(a.get('reason'),str) or len(a['reason'])>1000: raise ValueError('Provide a short reason.')
    if kind=='stop': return a
    if kind=='key':
        if a.get('key') not in ('Tab','Shift+Tab','Enter','Space','ArrowDown','ArrowUp','Escape'):
            raise ValueError('Key not allowed.')
        return a
    if profile['keyboard_only'] and kind=='click': raise ValueError('Pointer clicks disabled for this profile.')
    if type(a.get('target')) is not int: raise ValueError('Target must be an observed control ID.')
    targets={x['id']:x for x in controls}
    if a['target'] not in targets: raise ValueError('Unknown control ID.')
    target=targets[a['target']]
    if target.get('disabled'): raise ValueError('Control is disabled.')
    if target.get('type') in ('password','file','hidden'): raise ValueError('Sensitive input type blocked.')
    if kind in ('fill','select'):
        if a.get('data_key') not in data: raise ValueError('Use a configured synthetic value, not model-generated text.')
        if kind=='fill' and target['tag'] not in ('input','textarea'): raise ValueError('Not a text field.')
        if kind=='select' and target['tag']!='select': raise ValueError('Not a select.')
    return a

def read_config(path):
    return validate_config(json.loads(path.read_text()))
