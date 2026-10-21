import hashlib
import io
import os
import tarfile
import urllib.request
from pathlib import Path

VERSION = '7.6.6'
SHA256 = 'ddbc4a2d113bbd46d283cfedcbcd117a70caefd7673f41f2b4e0000badf103bc'
url = f'https://github.com/PowerShell/PowerShell/releases/download/v{VERSION}/powershell-{VERSION}-linux-x64.tar.gz'
payload = urllib.request.urlopen(url, timeout=180).read()
assert hashlib.sha256(payload).hexdigest() == SHA256, 'PowerShell checksum mismatch'
destination = Path('/opt/powershell')
destination.mkdir(parents=True, exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
    archive.extractall(destination, filter='data')
os.chmod(destination / 'pwsh', 0o755)
Path('/usr/local/bin/pwsh').symlink_to(destination / 'pwsh')
