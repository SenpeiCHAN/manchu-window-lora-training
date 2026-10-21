from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


DB_PATH = os.getenv("LORA_STATE_DB", "/state/lora.db")
DATA_ROOT = Path(os.getenv("LORA_DATA_ROOT", "/data"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=30000")
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS datasets (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              path TEXT NOT NULL,
              version INTEGER NOT NULL DEFAULT 1,
              image_count INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS images (
              id TEXT PRIMARY KEY,
              dataset_id TEXT NOT NULL REFERENCES datasets(id),
              filename TEXT NOT NULL,
              path TEXT NOT NULL,
              caption TEXT NOT NULL DEFAULT '',
              width INTEGER,
              height INTEGER,
              has_caption INTEGER NOT NULL DEFAULT 0,
              UNIQUE(dataset_id, filename)
            );
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              status TEXT NOT NULL,
              payload TEXT NOT NULL,
              progress REAL NOT NULL DEFAULT 0,
              current_step INTEGER,
              total_steps INTEGER,
              message TEXT NOT NULL DEFAULT '',
              worker_id TEXT,
              created_at TEXT NOT NULL,
              started_at TEXT,
              finished_at TEXT,
              heartbeat_at TEXT,
              error TEXT
            );
            CREATE TABLE IF NOT EXISTS job_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_id TEXT NOT NULL REFERENCES jobs(id),
              event_type TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS artifacts (
              id TEXT PRIMARY KEY,
              job_id TEXT NOT NULL REFERENCES jobs(id),
              kind TEXT NOT NULL,
              path TEXT NOT NULL,
              metadata TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS job_metrics (
              job_id TEXT NOT NULL,
              step INTEGER NOT NULL,
              total INTEGER NOT NULL,
              loss REAL NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY(job_id, step)
            );
            CREATE TABLE IF NOT EXISTS caption_records (
              image_path TEXT PRIMARY KEY,
              source TEXT NOT NULL,
              wd14_caption TEXT,
              model_id TEXT,
              threshold REAL,
              job_id TEXT,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);
            CREATE INDEX IF NOT EXISTS idx_events_job_id ON job_events(job_id, id);
            """
        )


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def json_load(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def add_event(db: sqlite3.Connection, job_id: str, event_type: str, payload: dict[str, Any]) -> int:
    cursor = db.execute(
        "INSERT INTO job_events(job_id,event_type,payload,created_at) VALUES (?,?,?,?)",
        (job_id, event_type, json.dumps(payload, ensure_ascii=False), now_iso()),
    )
    return int(cursor.lastrowid)
