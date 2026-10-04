import time
from policy import validate_action

PROFILES=[
 {'id':'desktop','name':'Desktop exploratory journey','viewport':{'width':1280,'height':800},'keyboard_only':False,
  'instruction':'Explore the task from the supplied page without assuming prior service knowledge.'},
 {'id':'mobile','name':'Mobile focused journey','viewport':{'width':390,'height':844},'keyboard_only':False,
  'instruction':'Complete the same task in a narrow viewport. Do not assume the desktop layout.'},
 {'id':'keyboard','name':'Keyboard interaction journey','viewport':{'width':1280,'height':800},'keyboard_only':True,
  'instruction':'Navigate with Tab and activation keys. Fill/select only the focused field. This is not disability simulation.'}]

def run_journey(session,config,profile,decider,out,clock=time.perf_counter):
    started=clock();model_total=0.;browser_total=0.;steps=[];issues=[];usage=[]
    status='step_limit';detail='Configured step budget reached; task success was not observed.'
    out.mkdir(parents=True,exist_ok=True)
    def issue(kind,message,step,screen,points):
        if not any(x['kind']==kind and x['message']==message for x in issues):
            issues.append({'kind':kind,'message':message,'step':step,'screenshot':screen,
                           'gds_points':points,'human_decision':'pending','severity':'not_assessed'})
    try:
        before=clock()
        try:session.start(config['url'])
        finally:browser_total+=clock()-before
        if session.success(config['success_text']):
            status='invalid_success_marker';detail='Success marker was already visible before any action; choose a discriminating marker.'
        else:
            for n in range(1,config.get('max_steps',16)+1):
                if clock()-started>=config.get('max_seconds',300):
                    status='time_limit';detail='Automated run budget reached.';break
                observation=session.observe()
                screen=f'step-{n:02d}.png';session.screenshot(out/screen)
                if observation.get('overflow'):
                    issue('potential_layout_barrier','Document width exceeds this viewport; verify whether horizontal scrolling obstructs the task.',n,screen,[4,5])
                for c in observation['controls']:
                    if not c.get('label') and c['tag'] in ('input','select','textarea') and c.get('type') not in ('hidden','submit','button','password'):
                        issue('potential_label_gap',f"Visible control {c['id']} has no label in this simple DOM extraction. Check its computed accessible name manually.",n,screen,[4,5])
                for alert in observation.get('alerts',[]):
                    if alert.strip():issue('visible_alert',alert,n,screen,[4])
                before=clock()
                remaining=max(1,config.get('max_seconds',300)-(before-started))
                try:
                    action,meta=decider({'task':config['task'],'profile':profile,'test_data':config['test_data'],
                        'observation':observation,'history':steps[-6:]},timeout=min(60,remaining))
                finally:
                    model_seconds=clock()-before;model_total+=model_seconds
                usage.append(meta)
                validate_action(action,observation['controls'],profile,config['test_data'])
                event={'step':n,'action':action,'screenshot':screen,'decision_seconds':round(model_seconds,4),
                       'browser_seconds':0.,'outcome':'not_executed'};steps.append(event)
                if clock()-started>=config.get('max_seconds',300):
                    status='time_limit';detail='Time budget ended while awaiting the decision.';break
                if action['action']=='stop':
                    event['outcome']='agent_stopped';status='agent_stopped';detail=action['reason'];break
                fresh=session.observe()
                if fresh['controls']!=observation['controls']:
                    event['outcome']='stale_observation';status='harness_stopped';detail='Page controls changed during decision; stopped to avoid a stale action.';break
                before=clock()
                try:
                    session.act(action,config['test_data'],profile['keyboard_only']);session.settle()
                finally:
                    elapsed=clock()-before;browser_total+=elapsed;event['browser_seconds']=round(elapsed,4)
                event['outcome']='executed'
                if session.success(config['success_text']):
                    status='success_marker_observed';detail='The configured exact visible success marker was observed after an action.';break
    except Exception as e:
        status='harness_error';detail=f'{type(e).__name__}: run interrupted; inspect configuration, agent action and test environment.'
        # Do not put exception bodies (potential page/credential content) in reports.
    finally:
        try:session.screenshot(out/'final.png')
        except Exception:pass
    wall=clock()-started
    return {'profile':profile,'status':status,'detail':detail,'steps':steps,'observations':issues,
            'wall_seconds':round(wall,4),'decision_seconds':round(model_total,4),
            'browser_seconds':round(browser_total,4),
            'other_seconds':round(max(0,wall-model_total-browser_total),4),
            'executed_actions':sum(s['outcome']=='executed' for s in steps),
            'usage':usage,'network_blocks':list(session.network),
            'final_screenshot':'final.png' if (out/'final.png').exists() else None}

def demo_decider(payload,timeout=60):
    """Deterministic fixture path, not AI or a simulated human finding."""
    controls=payload['observation']['controls'];keyboard=payload['profile']['keyboard_only']
    if keyboard:
        focus=next((c for c in controls if c.get('focused')),None)
        if not focus:return {'action':'key','key':'Tab','reason':'Move focus to the first control.'},{}
        if focus['tag']=='input':
            if not focus.get('value'):return {'action':'fill','target':focus['id'],'data_key':'postcode','reason':'Enter the configured fictional postcode.'},{}
            return {'action':'key','key':'Tab','reason':'Move to the next control.'},{}
        return {'action':'key','key':'Enter','reason':'Activate the focused control.'},{}
    field=next((c for c in controls if c['tag']=='input'),None)
    if field and not field.get('value'):
        return {'action':'fill','target':field['id'],'data_key':'postcode','reason':'Enter configured fixture data.'},{}
    button=next((c for c in controls if c['tag']=='button'),None)
    if button:return {'action':'click','target':button['id'],'reason':'Activate the fixture continue control.'},{}
    return {'action':'stop','reason':'No permitted fixture action remains.'},{}
