import hashlib,io,json,zipfile
from pathlib import Path
from PIL import Image,ImageOps
import numpy as np
root=Path('/data/manzhou'); train=root/'datasets/train'; review=root/'datasets/review';train.mkdir(parents=True,exist_ok=True);review.mkdir(parents=True,exist_ok=True)
rows=[]; seen=set()
with zipfile.ZipFile('/input/photos.zip') as z:
    entries=[x for x in z.infolist() if not x.is_dir()]
    for index,e in enumerate(entries):
        if Path(e.filename).suffix.lower() not in ('.jpg','.jpeg','.png'):
            rows.append({'source':e.filename,'status':'excluded_non_image'});continue
        try:
            raw=z.read(e); digest=hashlib.sha256(raw).hexdigest()
            if digest in seen:
                rows.append({'source':e.filename,'status':'exact_duplicate','sha256':digest});continue
            seen.add(digest)
            image=ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('RGB');original_size=image.size
            preview=image.copy();preview.thumbnail((512,512));gray=np.asarray(preview.convert('L'),dtype=np.float64);lap=-4*gray[1:-1,1:-1]+gray[:-2,1:-1]+gray[2:,1:-1]+gray[1:-1,:-2]+gray[1:-1,2:];sharpness=float(lap.var())
            status='review_blur' if sharpness<25 else 'train'
            image.thumbnail((1024,1024));filename=f'{index:04d}_{Path(e.filename).stem}.jpg'; dest=(review if status=='review_blur' else train)/filename
            image.save(dest,quality=95,optimize=True)
            rows.append({'source':e.filename,'path':str(dest),'sha256':digest,'original_size':original_size,'size':image.size,'sharpness':round(sharpness,2),'status':status})
        except Exception as exc:rows.append({'source':e.filename,'status':'decode_failed','error':str(exc)})
        if index%50==0:print(f'Prepared {index+1}/{len(entries)}',flush=True)
from collections import Counter
summary={'source_archive':'D:\\iCloud 照片 (1).zip','original_unchanged':True,'normalization':'EXIF orientation, RGB, longest side <=1024, JPEG quality95; no crop','blur_filter':'Laplacian variance on 512px preview <25 placed in review; heuristic, not definitive quality assessment','counts':dict(Counter(r['status'] for r in rows)),'train_path':str(train)}
(root/'reports/preparation-manifest.json').write_text(json.dumps({'summary':summary,'images':rows},ensure_ascii=False,indent=2),encoding='utf8')
(root/'reports/preparation-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

