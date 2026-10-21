"""Verify old project volumes before removing them. Never touches other projects."""
import hashlib
import sqlite3
from pathlib import Path

backup = Path('/data/backups/state-before-20261008.db')
backup.parent.mkdir(parents=True, exist_ok=True)
if backup.exists():
    if backup.stat().st_size == 0:
        backup.unlink()  # Empty file left by a failed attempt only.
    else:
        raise SystemExit('Recovery backup already exists; refusing to overwrite.')
with sqlite3.connect('/old-state/lora.db') as source, sqlite3.connect(backup) as target:
    source.backup(target)
    assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    print('Recovery backup:', backup, target.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 'jobs')
count = 0
for original in Path('/old-cache').rglob('*'):
    if original.is_file():
        migrated = Path('/data/cache') / original.relative_to('/old-cache')
        assert migrated.is_file(), f'Missing cache: {migrated}'
        assert hashlib.sha256(original.read_bytes()).digest() == hashlib.sha256(migrated.read_bytes()).digest(), f'Changed cache: {migrated}'
        count += 1
print('Cache verified:', count, 'files; old project volumes can be removed.')
