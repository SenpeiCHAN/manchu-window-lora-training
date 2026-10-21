import json
import zipfile
from collections import Counter
from pathlib import PurePosixPath

with zipfile.ZipFile('/input/photos.zip') as archive:
    files = [x for x in archive.infolist() if not x.is_dir()]
    report = {'files': len(files), 'uncompressed_bytes': sum(x.file_size for x in files), 'extensions': dict(Counter(PurePosixPath(x.filename).suffix.lower() for x in files)), 'sample': [{'name':x.filename,'bytes':x.file_size} for x in files[:18]]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
