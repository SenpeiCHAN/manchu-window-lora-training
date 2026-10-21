import json,shutil
from pathlib import Path
from collections import Counter
root=Path('/data/manzhou');manifest=json.loads((root/'reports/preparation-manifest.json').read_text(encoding='utf8'))
for row in manifest['images']:
    if Path(row.get('source','')).name.upper()=='IMG_9993.JPG' and row['status']=='train':
        old=Path(row['path']);new=root/'datasets/review'/old.name;shutil.move(old,new);row.update(path=str(new),status='review_manual_blur',reason='visible motion blur in 20-image contact sheet')
manifest['summary']['counts']=dict(Counter(r['status'] for r in manifest['images']))
(root/'reports/preparation-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
(root/'reports/preparation-summary.json').write_text(json.dumps(manifest['summary'],ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(manifest['summary'],ensure_ascii=False,indent=2))
