"""Temporary loopback-only SSH server for browser acceptance, never for deployment."""
import os
import socket
import threading
from pathlib import Path
import paramiko
from test_ssh_integration import HOST_KEY, Server

Path('/tmp/lora-ssh-ui-fixture.pid').write_text(str(os.getpid()))
listener = socket.socket()
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind(('127.0.0.1', 22222))
listener.listen()

def serve(connection):
    try:
        with paramiko.Transport(connection) as transport:
            transport.add_server_key(HOST_KEY)
            transport.start_server(server=Server())
            channels = []
            while transport.is_active():
                channel = transport.accept(.2)
                if channel: channels.append(channel)
                channels = [channel for channel in channels if not channel.closed]
    except (OSError, EOFError, paramiko.SSHException): pass

while True:
    connection, _ = listener.accept()
    threading.Thread(target=serve, args=(connection,), daemon=True).start()
