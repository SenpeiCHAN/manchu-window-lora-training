import json, zipfile, io
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
root=Path('/data/manzhou')
with zipfile.ZipFile('/input/photos.zip') as z:
    items=[i for i in z.infolist() if i.filename.lower().endswith(('.jpg','.jpeg','.png'))]
    sample=[items[round(i*(len(items)-1)/19)] for i in range(20)]
    canvas=Image.new('RGB',(1200,1100),'#eeeeee'); draw=ImageDraw.Draw(canvas)
    report=[]
    for index,entry in enumerate(sample):
        with Image.open(io.BytesIO(z.read(entry))) as original:
            image=ImageOps.exif_transpose(original).convert('RGB'); size=image.size
            image.thumbnail((290,190))
            x=(index%4)*300+(300-image.width)//2; y=(index//4)*220
            canvas.paste(image,(x,y));draw.text(((index%4)*300+8,y+195),Path(entry.filename).name,fill='#111111')
            report.append({'name':entry.filename,'dimensions':size})
    canvas.save(root/'reports/sample-contact-sheet.jpg',quality=92)
    (root/'reports/sample-inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('20 image sample contact sheet saved to E reports; source archive unchanged',flush=True)
