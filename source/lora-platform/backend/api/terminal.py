"""Command console in the API container, plus SSH command output. No Docker socket."""
import os
import signal
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.shared.db import DATA_ROOT, now_iso

router = APIRouter(prefix='/api/terminal', tags=['terminal'])
sessions = {}
lock = threading.RLock()


class Command(BaseModel):
    engine: Literal['bash', 'powershell', 'python']
    command: str = Field(min_length=1, max_length=16000)
    cwd: str = '/data'
    timeout: int = Field(default=120, ge=1, le=600)


def new_session(engine):
    with lock:
        for key in list(sessions):
            if sessions[key]['status'] != 'running' and time.monotonic() - sessions[key]['created_monotonic'] > 900:
                del sessions[key]
        if sum(s['status'] == 'running' for s in sessions.values()) >= 3:
            raise HTTPException(409, '已有三个命令运行中，请先停止或等待完成。')
        sid = 'console_' + uuid.uuid4().hex[:12]
        sessions[sid] = {'id': sid, 'engine': engine, 'status': 'running', 'output': '', 'exit_code': None, 'created_at': now_iso(), 'created_monotonic': time.monotonic(), 'process': None, 'channel': None, 'cancelled': False}
        return sid


def append_output(sid, value):
    with lock:
        item = sessions[sid]
        item['output'] = (item['output'] + value)[-200000:]


def finish(sid, code, status=None):
    with lock:
        sessions[sid]['exit_code'] = code
        sessions[sid]['status'] = status or ('succeeded' if code == 0 else 'failed')
        sessions[sid]['process'] = None
        sessions[sid]['channel'] = None


@router.get('/capabilities')
def capabilities():
    import shutil
    return {'location': 'API 容器（Linux）', 'engines': [{'id': 'bash', 'available': bool(shutil.which('bash'))}, {'id': 'powershell', 'available': bool(shutil.which('pwsh'))}, {'id': 'python', 'available': True}]}


@router.post('/commands', status_code=201)
def start(body: Command):
    cwd = Path(body.cwd).resolve()
    if (cwd != DATA_ROOT and DATA_ROOT not in cwd.parents) or not cwd.is_dir():
        raise HTTPException(400, '工作目录必须是 /data 内已有的目录。')
    sid = new_session(body.engine)
    def run():
        timed_out = threading.Event()
        process = None
        timer = None
        try:
            args = {'bash': ['bash', '-c', body.command], 'powershell': ['pwsh', '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', body.command], 'python': ['python', '-u', '-c', body.command]}[body.engine]
            home = DATA_ROOT / 'terminal' / 'home'
            home.mkdir(parents=True, exist_ok=True)
            env = dict(os.environ, HOME=str(home), PIP_CACHE_DIR='/data/cache/pip', XDG_CACHE_HOME='/data/cache/terminal', PYTHONUNBUFFERED='1', TERM='dumb', POWERSHELL_TELEMETRY_OPTOUT='1')
            process = subprocess.Popen(args, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
            with lock:
                sessions[sid]['process'] = process
                cancelled = sessions[sid]['cancelled']
            def stop_timeout():
                if process.poll() is None:
                    timed_out.set()
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
            timer = threading.Timer(body.timeout, stop_timeout); timer.start()
            if cancelled:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
            import codecs
            decoder = codecs.getincrementaldecoder('utf-8')('replace')
            while chunk := process.stdout.read1(4096):
                append_output(sid, decoder.decode(chunk))
            append_output(sid, decoder.decode(b'', final=True))
            code = process.wait()
            finish(sid, code, 'timed_out' if timed_out.is_set() else 'cancelled' if sessions[sid]['cancelled'] else None)
        except Exception as error:
            append_output(sid, f'\n命令启动失败：{error}')
            finish(sid, -1)
        finally:
            if timer: timer.cancel()
    threading.Thread(target=run, daemon=True).start()
    return {'id': sid}


@router.get('/commands/{sid}')
def read(sid: str):
    with lock:
        if sid not in sessions:
            raise HTTPException(404, '命令记录已过期或服务已重启。')
        return {k: v for k, v in sessions[sid].items() if k in {'id','engine','status','output','exit_code','created_at'}}


@router.post('/commands/{sid}/stop')
def stop(sid: str):
    with lock:
        if sid not in sessions: raise HTTPException(404, '命令不存在。')
        item = sessions[sid]
        if item['status'] != 'running': return {'status': item['status']}
        item['cancelled'] = True
        if item['process'] and item['process'].poll() is None:
            try: os.killpg(item['process'].pid, signal.SIGKILL)
            except ProcessLookupError: pass
        if item['channel']: item['channel'].close()
    return {'status': 'stopping'}
