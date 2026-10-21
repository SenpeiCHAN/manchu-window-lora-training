import json,time,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
root=Path('/data/manzhou');jobid=json.loads((root/'configs/train-v2-job.json').read_text(encoding='utf8'))['id']
while True:
    with urllib.request.urlopen('http://api:8000/api/jobs/'+jobid,timeout=30) as r:job=json.load(r)
    with urllib.request.urlopen('http://api:8000/api/jobs/'+jobid+'/metrics',timeout=30) as r:metrics=json.load(r)
    points=metrics.get('points',[]) if isinstance(metrics,dict) else metrics
    row={k:job.get(k) for k in ('id','status','current_step','total_steps','progress','message','error')};row['time']=datetime.now(timezone(timedelta(hours=8))).isoformat();row['last_metric']=points[-1] if points else None
    with (root/'logs/training-v2-monitor.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(json.dumps(row,ensure_ascii=False),flush=True)
    if job['status'] in ('succeeded','failed','cancelled','interrupted'):
        (root/'reports/train-v2-final.json').write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding='utf8')
        (root/'reports/train-v2-metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf8')
        break
    time.sleep(45)
