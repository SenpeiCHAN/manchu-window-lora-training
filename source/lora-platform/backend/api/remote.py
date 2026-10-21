"""SSH extension boundary. Credentials stay in memory; no remote job execution."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import socket
import shlex
import threading
import time
from pathlib import Path
from typing import Literal

import paramiko
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.shared.db import DB_PATH
from backend.api.terminal import new_session, append_output, finish, sessions, lock

router = APIRouter(prefix='/api/remote/ssh', tags=['remote'])
PROFILE_PATH = Path(DB_PATH).parent / 'ssh-profile.json'


class SshProfile(BaseModel):
    provider: Literal['autodl', 'other'] = 'autodl'
    host: str = Field(default='', max_length=253, pattern=r'^[a-zA-Z0-9.:-]*$')
    port: int = Field(default=22, ge=1, le=65535)
    username: str = Field(default='root', min_length=1, max_length=64, pattern=r'^[a-zA-Z0-9_.-]+$')
    workdir: str = Field(default='/root/autodl-tmp/LoRA', max_length=500, pattern=r'^/[^\x00\r\n]*$')
    fingerprint: str = Field(default='', max_length=100, pattern=r'^(SHA256:[A-Za-z0-9+/]+)?$')


def fingerprint(key: paramiko.PKey) -> str:
    digest = hashlib.sha256(key.asbytes()).digest()
    return 'SHA256:' + base64.b64encode(digest).decode().rstrip('=')


def open_transport(profile: SshProfile) -> paramiko.Transport:
    if not profile.host:
        raise HTTPException(400, '请填写服务器地址。')
    sock = socket.create_connection((profile.host, profile.port), timeout=8)
    transport = paramiko.Transport(sock)
    transport.banner_timeout = 8
    transport.auth_timeout = 8
    transport.channel_timeout = 8
    try:
        transport.start_client(timeout=8)
        if not transport.is_active():
            raise paramiko.SSHException('SSH handshake incomplete')
        return transport
    except Exception:
        transport.close()
        raise


@router.get('/config')
def get_config() -> dict:
    if PROFILE_PATH.exists():
        return SshProfile.model_validate_json(PROFILE_PATH.read_text()).model_dump()
    return SshProfile().model_dump()


@router.put('/config')
def save_config(profile: SshProfile) -> dict:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PROFILE_PATH.with_suffix('.tmp')
    temporary.write_text(profile.model_dump_json(), encoding='utf-8')
    temporary.replace(PROFILE_PATH)
    return profile.model_dump()


@router.post('/probe')
def probe(profile: SshProfile) -> dict:
    try:
        with open_transport(profile) as transport:
            key = transport.get_remote_server_key()
            return {'fingerprint': fingerprint(key), 'key_type': key.get_name()}
    except HTTPException:
        raise
    except (OSError, EOFError, paramiko.SSHException):
        raise HTTPException(400, '无法完成 SSH 握手，请检查地址、端口及服务器状态。')


@router.post('/test')
def test_connection(profile: str = Form(...), password: str = Form(''), passphrase: str = Form(''), private_key: UploadFile | None = File(None)) -> dict:
    try:
        config = SshProfile.model_validate_json(profile)
    except ValueError:
        raise HTTPException(400, 'SSH 配置格式无效。')
    if not config.fingerprint:
        raise HTTPException(400, '请先获取并确认服务器指纹。')
    key_text = None
    if private_key:
        raw = private_key.file.read(65537)
        if len(raw) > 65536:
            raise HTTPException(400, '私钥文件过大。')
        try:
            key_text = raw.decode('utf-8')
        except UnicodeError:
            raise HTTPException(400, '私钥文件必须为文本格式。')
    try:
        with open_transport(config) as transport:
            if fingerprint(transport.get_remote_server_key()) != config.fingerprint:
                raise HTTPException(400, '服务器指纹已变化，连接已停止，请核实后重新确认。')
            if key_text:
                key = None
                for key_class in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
                    try:
                        key = key_class.from_private_key(io.StringIO(key_text), password=passphrase or None)
                        break
                    except (paramiko.SSHException, ValueError):
                        continue
                if key is None:
                    raise HTTPException(400, '私钥格式或私钥口令无效。')
                transport.auth_publickey(config.username, key)
            elif password:
                transport.auth_password(config.username, password, fallback=False)
            else:
                raise HTTPException(400, '请输入密码或选择私钥文件。')
            if not transport.is_authenticated():
                raise HTTPException(400, '身份验证未完成。')
            # SFTP avoids interpolation into a shell and never creates remote files.
            exists = None
            try:
                transport.open_session(timeout=8).close()
                with paramiko.SFTPClient.from_transport(transport) as sftp:
                    exists = bool(sftp.stat(config.workdir))
            except (OSError, paramiko.SSHException):
                pass
            return {'connected': True, 'username': config.username, 'workdir_exists': exists, 'message': 'SSH 身份验证成功；远程训练调度尚未启用。'}
    except HTTPException:
        raise
    except paramiko.AuthenticationException:
        raise HTTPException(400, 'SSH 身份验证失败，请检查用户名及凭据。')
    except (OSError, EOFError, paramiko.SSHException):
        raise HTTPException(400, 'SSH 连接失败，请检查服务器与网络状态。')


@router.post('/command', status_code=201)
def start_remote_command(profile: str = Form(...), command: str = Form(...), password: str = Form(''), passphrase: str = Form(''), private_key: UploadFile | None = File(None), timeout: int = Form(120)):
    try: config = SshProfile.model_validate_json(profile)
    except ValueError: raise HTTPException(400, 'SSH 配置格式无效。')
    if not config.fingerprint: raise HTTPException(400, '请先确认服务器指纹。')
    if not 1 <= len(command) <= 16000 or not 1 <= timeout <= 600: raise HTTPException(400, '命令长度或超时值无效。')
    key_text = None
    if private_key:
        raw = private_key.file.read(65537)
        if len(raw) > 65536: raise HTTPException(400, '私钥文件过大。')
        try: key_text = raw.decode('utf-8')
        except UnicodeError: raise HTTPException(400, '私钥格式无效。')
    if not password and not key_text: raise HTTPException(400, '请输入密码或选择私钥。')
    sid = new_session('ssh')
    def run():
        channel = None
        try:
            append_output(sid, f'正在连接 {config.host}:{config.port} …\n')
            with open_transport(config) as transport:
                if fingerprint(transport.get_remote_server_key()) != config.fingerprint:
                    raise HTTPException(400, '服务器指纹变化，已停止连接。')
                if key_text:
                    key = None
                    for cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
                        try: key = cls.from_private_key(io.StringIO(key_text), password=passphrase or None); break
                        except (paramiko.SSHException, ValueError): pass
                    if key is None: raise HTTPException(400, '私钥或私钥口令无效。')
                    transport.auth_publickey(config.username, key)
                else:
                    transport.auth_password(config.username, password, fallback=False)
                channel = transport.open_session(timeout=8)
                channel.settimeout(8)
                with lock:
                    sessions[sid]['channel'] = channel
                    cancelled = sessions[sid]['cancelled']
                if cancelled: finish(sid, -1, 'cancelled'); return
                append_output(sid, f'SSH 已连接 · 用户 {config.username} · 工作目录 {config.workdir}\n')
                # Explicit commands execute only after the user's button action.
                channel.exec_command(f'cd -- {shlex.quote(config.workdir)} && ( {command}\n)')
                deadline = time.monotonic() + timeout
                import codecs
                dec = codecs.getincrementaldecoder('utf-8')('replace')
                err_dec = codecs.getincrementaldecoder('utf-8')('replace')
                while True:
                    if sessions[sid]['cancelled']:
                        append_output(sid, '\nSSH 通道已关闭；远端后台程序状态需另行核实。\n'); finish(sid, -1, 'cancelled'); return
                    if time.monotonic() > deadline:
                        append_output(sid, '\n等待输出超时，SSH 通道已关闭。\n'); finish(sid, -1, 'timed_out'); return
                    if channel.recv_ready(): append_output(sid, dec.decode(channel.recv(4096)))
                    if channel.recv_stderr_ready(): append_output(sid, err_dec.decode(channel.recv_stderr(4096)))
                    if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                        append_output(sid, dec.decode(b'', final=True) + err_dec.decode(b'', final=True)); finish(sid, channel.recv_exit_status()); return
                    time.sleep(.05)
        except HTTPException as error: append_output(sid, error.detail); finish(sid, -1)
        except paramiko.AuthenticationException: append_output(sid, 'SSH 身份验证失败。'); finish(sid, -1)
        except (OSError, EOFError, paramiko.SSHException): append_output(sid, 'SSH 命令执行失败，请检查连接与服务器状态。'); finish(sid, -1)
        finally:
            if channel: channel.close()
    threading.Thread(target=run, daemon=True).start()
    return {'id': sid}
