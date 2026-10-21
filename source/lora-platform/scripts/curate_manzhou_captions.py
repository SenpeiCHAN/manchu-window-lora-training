import json,urllib.request,collections
from pathlib import Path
root=Path('/data/manzhou')
def call(path,data=None,method=None):
    req=urllib.request.Request('http://127.0.0.1:8000/api'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'},method=method)
    with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)
dsid=json.loads((root/'configs/dataset.json').read_text(encoding='utf-8-sig'))['id']
data=call('/datasets/'+dsid);frequency=collections.Counter();rows=[]
for image in data['images']:
    raw=image.get('wd14_caption')
    if raw is None:raise RuntimeError('Missing WD14: '+image['filename'])
    tags=[t.strip().replace('_',' ') for t in raw.split(',') if t.strip()]
    frequency.update(tags)
    # Preserve raw machine tags; prepend the dataset's explicit concept phrase.
    prefix=['manzhou_window','stained glass window']
    caption=', '.join(prefix+[t for t in tags if t not in prefix])
    call('/datasets/'+dsid+'/images/'+image['id']+'/caption',{'caption':caption,'source':'manual'},'PUT')
    rows.append({'image':image['filename'],'raw_wd14':raw,'training_caption':caption,'curation':'assistant added dataset concept prefix; individual raw tags not all manually verified'})
report={'count':len(rows),'trigger':'manzhou_window','class_phrase':'stained glass window','raw_wd14_preserved':True,'source_note':'UI manual means edited training caption; here edited by assistant, not individually verified by human','top_tags':frequency.most_common(30),'captions':rows}
(root/'reports/caption-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='captions'},ensure_ascii=False,indent=2))
