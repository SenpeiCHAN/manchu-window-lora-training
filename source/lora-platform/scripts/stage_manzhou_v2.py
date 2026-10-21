import json,os,shutil
from pathlib import Path
root=Path('/data/manzhou');old=root/'runs/jobs/job_f86f74424a51/training_dataset/1_train';clean=root/'datasets/train';new=root/'datasets/prepared-v2/1_train';new.mkdir(parents=True,exist_ok=True)
images=sorted(clean.glob('*.jpg'));assert len(images)==671
stats={'hardlinks':0,'copies':0,'captions':0,'images':len(images),'source_cache':str(old),'new_dataset':str(new),'source_status':'previous 172-step run failed; cached latents reusable because model and normalized pixels are unchanged'}
for i,image in enumerate(images):
    cached=list(old.glob(image.stem+'_*_sd.npz'));assert len(cached)==1,(image.name,cached)
    for source in (image,cached[0]):
        target=new/source.name
        if target.exists():
            assert target.stat().st_size==source.stat().st_size,target
            continue
        try:os.link(source,target);stats['hardlinks']+=1
        except OSError:shutil.copy2(source,target);stats['copies']+=1
    caption=image.with_suffix('.txt');content=caption.read_text(encoding='utf8')
    assert content.startswith('manzhou_window, stained glass window'),caption
    (new/caption.name).write_text(content,encoding='utf8');stats['captions']+=1
    if i%100==0:print(f'staged {i+1}/671',flush=True)
assert len(list(new.glob('*.jpg')))==len(list(new.glob('*.txt')))==len(list(new.glob('*.npz')))==671
(root/'configs/prepared-v2.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(stats,ensure_ascii=False,indent=2),flush=True)
