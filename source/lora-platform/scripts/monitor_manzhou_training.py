import json,time,urllib.request
from pathlib import Path
root=Path('/data/manzhou'); jobid=json.loads((root/'configs/train-job.json').read_text())['id']
while True:
    with urllib.request.urlopen('http://api:8000/api/jobs/'+jobid,timeout=30) as r:job=json.load(r)
    with urllib.request.urlopen('http://api:8000/api/jobs/'+jobid+'/metrics',timeout=30) as r:metrics=json.load(r)
    row={k:job.get(k) for k in ('id','status','current_step','total_steps','progress','message','error')};row['time']=time.strftime('%Y-%m-%dT%H:%M:%S%z');row['metrics']=metrics[-1:] if isinstance(metrics,list) else metrics
    with (root/'logs/training-monitor.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(json.dumps(row,ensure_ascii=False),flush=True)
    if job['status'] in ('succeeded','failed','cancelled','interrupted'):
        (root/'reports/train-job-final.json').write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding='utf8')
        (root/'reports/training-metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf8')
        break
    time.sleep(45)
