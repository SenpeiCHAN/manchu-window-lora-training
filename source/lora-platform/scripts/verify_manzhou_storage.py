import json
from pathlib import Path
from backend.worker.main import job_workspace, comfy_workflow
root = Path('/data/manzhou')
proof = {'dataset_root': str(root), 'job_workspace': str(job_workspace('storage_validation', {'train_data_dir':'/data/manzhou/datasets/train'})), 'result':'E storage mount write passed'}
(root/'reports/storage-validation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
assert str(job_workspace('storage_validation', {'train_data_dir':'/data/manzhou/datasets/train'})) == '/data/runs/manzhou/jobs/storage_validation'
print(json.dumps(proof,ensure_ascii=False,indent=2))
