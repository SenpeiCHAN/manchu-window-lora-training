"""Run in the worker container after API and worker have stopped."""
import shutil
import sqlite3
from pathlib import Path

root = Path('/data')
target = root / 'state' / 'lora.db'
target.parent.mkdir(parents=True, exist_ok=True)
if target.exists():
    raise SystemExit('Target DB already exists; refusing to overwrite it.')
with sqlite3.connect('/state/lora.db') as source, sqlite3.connect(target) as destination:
    source.backup(destination)
    assert destination.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    print('Database backup verified:', destination.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 'jobs')
for item in Path('/cache').iterdir():
    destination = root / 'cache' / item.name
    if destination.exists():
        raise SystemExit(f'Cache destination already exists: {destination}')
    if item.is_dir():
        shutil.copytree(item, destination, symlinks=True)
    else:
        shutil.copy2(item, destination)
print('Storage migration complete; original Docker volumes retained for recovery.')
