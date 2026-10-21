import json,collections
from pathlib import Path
from backend.shared.db import connect,now_iso
root=Path('/data/manzhou')
allowed=set('no humans|window|stained glass|indoors|outdoors|flower|still life|scenery|picture frame|tree|painting (object)|brick wall|butterfly|reflection|plant|architecture|door|cloud|lantern|building|glass|wall|wooden floor|wooden wall|ceiling|floor|tile floor|stairs|roof|geometric pattern|floral print|mosaic|chinese text|traditional architecture|east asian architecture|frame'.split('|'))
with connect() as db:
    images=db.execute('SELECT i.*,cr.wd14_caption FROM images i JOIN caption_records cr ON i.path=cr.image_path WHERE i.dataset_id=?',('ds_f7c16f238a94',)).fetchall()
assert len(images)==671
rows=[];removed=collections.Counter()
for image in images:
    path=Path(image['path']).with_suffix('.txt');previous=path.read_text(encoding='utf8')
    if not previous.startswith('manzhou_window, stained glass window'):raise RuntimeError('Unexpected caption; refusing overwrite '+str(path))
    tags=[t.strip().replace('_',' ') for t in image['wd14_caption'].split(',') if t.strip()]
    kept=[t for t in tags if t in allowed];removed.update(t for t in tags if t not in allowed)
    caption=', '.join(['manzhou_window','stained glass window']+kept)
    path.write_text(caption,encoding='utf8');rows.append({'id':image['id'],'image':image['filename'],'raw_wd14':image['wd14_caption'],'training_caption':caption})
with connect() as db:
    db.execute('BEGIN IMMEDIATE')
    for row in rows:
        db.execute('UPDATE images SET caption=?,has_caption=1 WHERE id=?',(row['training_caption'],row['id']))
        db.execute('UPDATE caption_records SET source=?,updated_at=? WHERE image_path=(SELECT path FROM images WHERE id=?)',('manual',now_iso(),row['id']))
    db.execute('COMMIT')
report={'count':len(rows),'policy':'Conservative architectural vocabulary; assistant rule-based edit, not individual human verification','allowed_tags':sorted(allowed),'removed_tags':removed.most_common(),'raw_wd14_preserved':True,'captions':rows}
(root/'reports/caption-filter.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='captions'},ensure_ascii=False,indent=2))

