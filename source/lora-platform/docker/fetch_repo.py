from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

import requests


repo = os.environ["REPO"]
commit = os.environ["COMMIT"]
target = Path(os.environ["TARGET"])
url = f"https://github.com/{repo}/archive/{commit}.zip"
response = requests.get(url, timeout=(30, 180), allow_redirects=True)
response.raise_for_status()
with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
    root = archive.namelist()[0].split("/", 1)[0]
    for member in archive.infolist():
        relative = Path(member.filename).relative_to(root)
        if not relative.parts:
            continue
        destination = target / relative
        if member.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(member))
print(f"fetched {repo}@{commit} to {target}")
