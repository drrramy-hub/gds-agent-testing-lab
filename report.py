import csv
import html
import json

# Short project paraphrases; numbers map to the official Service Standard.
POINTS={1:'User understanding',2:'End-to-end problem coverage',3:'Cross-channel continuity',
4:'Task simplicity',5:'Inclusive access',6:'Team capabilities',7:'Agile delivery practice',
8:'Ongoing improvement',9:'Security and privacy governance',10:'Success measures and reporting',
11:'Technology decisions',12:'Source-code openness',13:'Shared standards and patterns',14:'Operational dependability'}

def summary(runs):
    completed=sum(r['status']=='success_marker_observed' for r in runs)
    return {'runs':len(runs),'success_marker_observed':completed,
            'automated_completion_fraction':f'{completed}/{len(runs)}',
            'mean_wall_seconds':sum(r['wall_seconds'] for r in runs)/len(runs) if runs else None}

def write_report(folder,report):
    report['summary']=summary(report['runs'])
    report['gds_evidence']=[{'point':n,'topic':label,
        'status':'limited_journey_evidence' if n in (4,5,10) else 'not_assessed',
        'note':('Review the trace; no compliance verdict.' if n in (4,5) else
                'Automated operational timing only; not public service-performance evidence.' if n==10 else
                'Requires additional human, organisational or technical assessment.')}
        for n,label in POINTS.items()]
    (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (folder/'timings.csv').open('w',newline='') as f:
        fields=['profile','status','wall_seconds','decision_seconds','browser_seconds','other_seconds','executed_actions']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in report['runs']:w.writerow({**{k:r[k] for k in fields if k!='profile'},'profile':r['profile']['id']})
    esc=lambda x:html.escape(str(x),quote=True)
    body=''
    for r in report['runs']:
        body+=f'<section><h2>{esc(r["profile"]["name"])}</h2><p class="badge">{esc(r["status"])}</p><p>{esc(r["detail"])}</p>'
        body+=f'<div class="metrics"><div><b>{r["wall_seconds"]:.2f}s</b>Total run</div><div><b>{r["decision_seconds"]:.2f}s</b>Decision time</div><div><b>{r["browser_seconds"]:.2f}s</b>Browser actions + waits</div></div>'
        body+='<h3>Observed points for review</h3>'
        if not r['observations']:body+='<p>No observations from the limited automated checks. This is not a usability or accessibility pass.</p>'
        for issue in r['observations']:
            body+=f'<article><strong>{esc(issue["kind"])}</strong><p>{esc(issue["message"])}</p><small>Step {issue["step"]} · GDS points {esc(issue["gds_points"])} · Human review pending</small></article>'
        body+='<h3>Action trace</h3><table><tr><th>Step</th><th>Action / rationale</th><th>Decision</th><th>Browser</th><th>Evidence</th></tr>'
        for s in r['steps']:
            path=f'{r["profile"]["id"]}/{s["screenshot"]}'
            body+=f'<tr><td>{s["step"]}</td><td>{esc(s["action"]["action"])} · {esc(s["action"]["reason"])}<br>{esc(s["outcome"])}</td><td>{s["decision_seconds"]:.2f}s</td><td>{s["browser_seconds"]:.2f}s</td><td><a href="{esc(path)}">Before action</a></td></tr>'
        body+='</table>'
        if r['final_screenshot']:body+=f'<details><summary>Final screenshot</summary><img alt="Final test state" src="{esc(r["profile"]["id"])}/final.png"></details>'
        body+='</section>'
    coverage=''.join(f'<tr><td>{g["point"]}</td><td>{esc(g["topic"])}</td><td>{esc(g["status"])}</td></tr>' for g in report['gds_evidence'])
    template='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GDS Agent Testing Lab — report</title><style>
body{margin:0;background:#f5f3ee;color:#162e36;font:15px/1.6 system-ui,sans-serif}header{padding:44px 6%;background:#14343f;color:white}h1{font-size:42px;line-height:1.1}main{max-width:1200px;margin:auto;padding:30px}section{background:white;border:1px solid #d6dedd;border-radius:14px;padding:25px;margin-bottom:24px}.metrics{display:flex;gap:30px;flex-wrap:wrap}.metrics b{display:block;font-size:27px}.badge{font-weight:bold;color:#1e6570}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #ddd;overflow-wrap:anywhere}article{background:#edf4f3;padding:15px;margin:10px 0}img{max-width:100%}a{color:#1b6875}small{color:#52676a}summary{cursor:pointer}@media(max-width:600px){main{padding:12px}section{padding:15px}h1{font-size:32px}td,th{padding:6px;font-size:12px}}</style>'''
    rendered=template+f'<header><p>OPEN-SOURCE / MICROSOFT FOUNDRY</p><h1>GDS Agent Testing Lab</h1><p>{esc(report["mode"])} · {esc(report["created_at"])}</p><p>Automated journeys, not research participants. Timings are not human completion times.</p></header><main><section><h2>Run summary</h2><p>{esc(report["task"])}</p><p>Success marker observed: {esc(report["summary"]["automated_completion_fraction"])} automated profiles.</p><p>Marker detection is not proof of back-end transaction success or user satisfaction.</p><a href="report.json">Full JSON</a> · <a href="timings.csv">Timing CSV</a></section>'+body+'<section><h2>GDS evidence coverage — no pass/fail judgement</h2><table><tr><th>Point</th><th>Topic (paraphrased)</th><th>Scope</th></tr>'+coverage+'</table><p><a href="https://www.gov.uk/service-manual/service-standard">Official Service Standard</a></p></section></main></html>'
    (folder/'report.html').write_text(rendered,encoding='utf-8')
