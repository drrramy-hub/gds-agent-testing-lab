import copy
import json
import tempfile
import unittest
from pathlib import Path
from policy import origin, validate_action, validate_config
from runner import run_journey, PROFILES
from report import write_report, summary

CONFIG={'url':'http://localhost:8090','task':'Complete fixture task','success_text':'Task complete','test_data':{'postcode':'ZZ1 1ZZ'},'max_steps':2,'max_seconds':10}
CONTROL={'id':0,'tag':'input','type':'text','label':'Postcode','value':'','disabled':False,'focused':True}

class Session:
    network=[]
    def __init__(self,initial=False,stale=False): self.done=initial; self.stale=stale; self.reads=0; self.actions=0
    def start(self,url): pass
    def success(self,marker): return self.done
    def observe(self):
        self.reads+=1
        c=dict(CONTROL)
        if self.stale and self.reads>1:c['value']='changed'
        return {'controls':[c],'overflow':False,'alerts':[]}
    def screenshot(self,path): path.write_bytes(b'fixture placeholder')
    def act(self,*args): self.actions+=1;self.done=True
    def settle(self): pass

def decide(payload,timeout): return {'action':'fill','target':0,'data_key':'postcode','reason':'Enter fixture data'},{}

class CoreTests(unittest.TestCase):
    def run_case(self,session=None,decider=decide):
        with tempfile.TemporaryDirectory() as t:
            return run_journey(session or Session(),CONFIG,PROFILES[0],decider,Path(t))
    def test_success_requires_action(self):
        s=Session(initial=True);r=self.run_case(s)
        self.assertEqual(r['status'],'invalid_success_marker');self.assertEqual(s.actions,0)
    def test_success_trace_and_timing(self):
        r=self.run_case();self.assertEqual(r['status'],'success_marker_observed');self.assertEqual(r['executed_actions'],1)
        self.assertAlmostEqual(r['wall_seconds'],r['decision_seconds']+r['browser_seconds']+r['other_seconds'],places=3)
    def test_stale_control_stops_action(self):
        s=Session(stale=True);r=self.run_case(s)
        self.assertEqual(r['status'],'harness_stopped');self.assertEqual(s.actions,0)
    def test_invalid_agent_action_does_not_execute(self):
        s=Session();r=self.run_case(s,lambda *a,**k:({'action':'execute_code','reason':'x'},{}))
        self.assertEqual(r['status'],'harness_error');self.assertEqual(s.actions,0)
    def test_error_body_not_disclosed(self):
        def fail(*a,**k):raise ValueError('secret exception body')
        r=self.run_case(decider=fail);self.assertNotIn('secret',json.dumps(r));self.assertEqual(r['status'],'harness_error')
    def test_keyboard_no_pointer(self):
        with self.assertRaises(ValueError):validate_action({'action':'click','target':0,'reason':'x'},[CONTROL],PROFILES[2],CONFIG['test_data'])
    def test_only_configured_input(self):
        with self.assertRaises(ValueError):validate_action({'action':'fill','target':0,'data_key':'invented','reason':'x'},[CONTROL],PROFILES[0],CONFIG['test_data'])
    def test_sensitive_fields_blocked(self):
        for kind in ('password','file','hidden'):
            with self.assertRaises(ValueError):validate_action({'action':'fill','target':0,'data_key':'postcode','reason':'x'},[{**CONTROL,'type':kind}],PROFILES[0],CONFIG['test_data'])
    def test_origin_and_budget_validation(self):
        self.assertEqual(origin('https://EXAMPLE.com/a'),('https','example.com',443))
        for url in ('file:///etc/passwd','https://user:pass@example.com'):
            with self.assertRaises(ValueError):origin(url)
        with self.assertRaises(ValueError):validate_config({**CONFIG,'max_steps':True})
    def test_report_escapes_untrusted_text_and_preserves_scope(self):
        r=self.run_case();r['detail']='<script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);data={'runs':[r],'mode':'test','created_at':'fixture','task':'fixture'};write_report(p,data)
            rendered=(p/'report.html').read_text()
            self.assertNotIn('<script>',rendered);self.assertIn('&lt;script&gt;',rendered)
            self.assertEqual(len(data['gds_evidence']),14)
            self.assertEqual(data['gds_evidence'][0]['status'],'not_assessed')
            self.assertTrue((p/'timings.csv').exists())
    def test_completion_does_not_count_errors(self):
        self.assertEqual(summary([{'status':'harness_error','wall_seconds':1}])['automated_completion_fraction'],'0/1')

if __name__=='__main__':unittest.main()
