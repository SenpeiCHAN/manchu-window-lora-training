import json,urllib.request,collections
from pathlib import Path
root=Path('/data/manzhou')
def call(path,data=None,method=None):
    req=urllib.request.Request('http://127.0.0.1:8000/api'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'},method=method)
    with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)
summary=json.loads((root/'reports/preparation-summary.json').read_text(encoding='utf-8-sig'))
existing=[d for d in call('/datasets') if d['path']=='/data/manzhou/datasets/train']
dataset=call('/datasets/'+existing[0]['id']) if existing else call('/datasets',{'name':'满洲窗 · E盘训练集','path':'/data/manzhou/datasets/train'})
assert dataset['image_count']==summary['counts']['train']
(root/'configs/dataset.json').write_text(json.dumps({k:v for k,v in dataset.items() if k!='images'},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in dataset.items() if k!='images'},ensure_ascii=False,indent=2))
