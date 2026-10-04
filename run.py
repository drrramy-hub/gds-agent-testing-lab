"""Run authorised staging journeys or the bundled fictional fixture."""
import argparse
import json
import threading
from datetime import datetime,timezone
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from policy import read_config
from runner import PROFILES,run_journey,demo_decider
from foundry import decide
from report import write_report

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path(__file__).parent/'example.json')
    parser.add_argument('--demo',action='store_true',help='Scripted browser run on bundled fictional fixture; no AI calls.')
    parser.add_argument('--i-own-test-environment',action='store_true',help='Confirm live target is your authorised test environment with synthetic data.')
    parser.add_argument('--output',type=Path,default=Path('reports'))
    args=parser.parse_args();config=read_config(args.config)
    if not args.demo and not args.i_own_test_environment:
        parser.error('Live actions require --i-own-test-environment and synthetic data. Use --demo for the bundled fixture.')
    from playwright.sync_api import sync_playwright
    from browser import Session
    server=None
    if args.demo:
        # Demo ignores custom task/data: ensure this is a fixed fixture test, not false analysis.
        config=read_config(Path(__file__).parent/'example.json')
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(Path(__file__).parent/'demo')))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        config['url']=f'http://127.0.0.1:{server.server_port}/index.html'
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=args.output/stamp;folder.mkdir(parents=True,exist_ok=False)
    report={'project':'GDS Agent Testing Lab','mode':'scripted_fixture_no_ai' if args.demo else 'foundry_agent_simulation',
            'created_at':datetime.now(timezone.utc).isoformat(),'task':config['task'],
            'target':config['url'],'success_marker':config['success_text'],
            'budgets':{'max_steps':config.get('max_steps',16),'max_seconds':config.get('max_seconds',300)},'runs':[]}
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            try:
                for profile in PROFILES:
                    print('Running:',profile['name'],flush=True)
                    session=Session(browser,config['url'],profile)
                    try:result=run_journey(session,config,profile,demo_decider if args.demo else decide,folder/profile['id'])
                    finally:session.close()
                    report['runs'].append(result);write_report(folder,report)
                    print(result['status'],f'{result["wall_seconds"]:.2f}s',flush=True)
            finally:browser.close()
    finally:
        if server:server.shutdown();server.server_close()
    print('Open:',(folder/'report.html').resolve())

if __name__=='__main__':main()
