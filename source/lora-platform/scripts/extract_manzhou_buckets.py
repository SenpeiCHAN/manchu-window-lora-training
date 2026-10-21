import json,re
from pathlib import Path
root=Path('/data/manzhou');text=(root/'runs/jobs/job_f86f74424a51/logs.txt').read_text(encoding='utf8')
buckets=[{'index':int(i),'width':int(w),'height':int(h),'images':int(n)} for i,w,h,n in re.findall(r'bucket (\d+): resolution \((\d+), (\d+)\),[^\n]*\n\s+count: (\d+)',text)]
assert sum(b['images'] for b in buckets)==671
report={'buckets':buckets,'total_images':671,'source':'actual sd-scripts training stdout','accelerator':'cuda','note':'Preserved aspect ratio via buckets; normalization did not crop; bucket fitting may trim edges'}
(root/'reports/actual-buckets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))
