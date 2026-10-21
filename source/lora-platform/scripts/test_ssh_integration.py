"""Real SSH protocol tests against a temporary local server, inside Docker."""
import io
import socket
import threading
import time
import subprocess
import unittest

import paramiko
from fastapi import HTTPException, UploadFile
from backend.api.remote import SshProfile, fingerprint, probe, test_connection, start_remote_command
from backend.api.terminal import read

HOST_KEY = paramiko.RSAKey.generate(2048)
CLIENT_KEY = paramiko.RSAKey.generate(2048)


class Server(paramiko.ServerInterface):
    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL if username == 'root' and password == 'test-only-password' else paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_SUCCESSFUL if username == 'root' and key == CLIENT_KEY else paramiko.AUTH_FAILED

    def check_channel_request(self, kind, channel_id):
        return paramiko.OPEN_SUCCEEDED if kind == 'session' else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_exec_request(self, channel, command):
        def execute():
            result = subprocess.run(['bash', '-c', command.decode()], capture_output=True)
            if result.stdout: channel.sendall(result.stdout)
            if result.stderr: channel.sendall_stderr(result.stderr)
            channel.send_exit_status(result.returncode)
            channel.close()
        threading.Thread(target=execute, daemon=True).start()
        return True

    def check_channel_subsystem_request(self, channel, name):
        return False


class SshIntegration(unittest.TestCase):
    def setUp(self):
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen()
        self.listener.settimeout(15)
        self.profile = SshProfile(host='127.0.0.1', port=self.listener.getsockname()[1], workdir='/tmp', fingerprint=fingerprint(HOST_KEY))
        def serve():
            try:
                connection, _ = self.listener.accept()
                with paramiko.Transport(connection) as transport:
                    transport.add_server_key(HOST_KEY)
                    transport.start_server(server=Server())
                    while transport.is_active():
                        channel = transport.accept(0.2)
                        if channel:
                            # SFTP deliberately unavailable: login must still be reported accurately.
                            pass
            except (OSError, EOFError, paramiko.SSHException):
                pass
        self.thread = threading.Thread(target=serve, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.listener.close()
        self.thread.join(timeout=2)

    def test_probe_returns_real_fingerprint(self):
        self.assertEqual(probe(self.profile)['fingerprint'], fingerprint(HOST_KEY))

    def test_password_login(self):
        result = test_connection(self.profile.model_dump_json(), 'test-only-password', '', None)
        self.assertTrue(result['connected'])
        self.assertIsNone(result['workdir_exists'])

    def test_private_key_login(self):
        buffer = io.StringIO()
        CLIENT_KEY.write_private_key(buffer)
        upload = UploadFile(io.BytesIO(buffer.getvalue().encode()), filename='test-only.pem')
        self.assertTrue(test_connection(self.profile.model_dump_json(), '', '', upload)['connected'])

    def test_wrong_password_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            test_connection(self.profile.model_dump_json(), 'wrong', '', None)
        self.assertIn('身份验证失败', error.exception.detail)

    def test_changed_host_key_is_rejected(self):
        self.profile.fingerprint = 'SHA256:wrong'
        with self.assertRaises(HTTPException) as error:
            test_connection(self.profile.model_dump_json(), 'test-only-password', '', None)
        self.assertIn('指纹已变化', error.exception.detail)

    def test_remote_command_streams_stdout_stderr_and_exit(self):
        result = start_remote_command(self.profile.model_dump_json(), 'printf "remote-output\\n"; printf "remote-error\\n" >&2; exit 7', 'test-only-password', '', None, 5)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            state = read(result['id'])
            if state['status'] != 'running': break
            time.sleep(.05)
        self.assertEqual(state['exit_code'], 7)
        self.assertEqual(state['status'], 'failed')
        self.assertIn('remote-output', state['output'])
        self.assertIn('remote-error', state['output'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
