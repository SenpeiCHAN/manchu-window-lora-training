"""Exercise running container console over HTTP, with real subprocesses."""
import json
import time
import unittest
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:8000/api/terminal'

def request(path, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    with urllib.request.urlopen(urllib.request.Request(BASE + path, data=payload, headers={'Content-Type': 'application/json'}), timeout=10) as response:
        return json.load(response)

def launch(engine, command, timeout=10):
    return request('/commands', {'engine': engine, 'command': command, 'cwd': '/data', 'timeout': timeout})['id']

def done(sid):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        state = request('/commands/' + sid)
        if state['status'] != 'running': return state
        time.sleep(.08)
    raise AssertionError('command did not finish')

class ConsoleTests(unittest.TestCase):
    def test_three_engines(self):
        for engine, command in [('powershell', 'Write-Output "container-powershell"; (Get-Location).Path'), ('bash', 'echo container-bash; pwd'), ('python', 'import os; print("container-python"); print(os.getcwd())')]:
            with self.subTest(engine=engine):
                state = done(launch(engine, command))
                self.assertEqual(state['exit_code'], 0)
                self.assertIn('/data', state['output'])
                self.assertIn('container-', state['output'])
    def test_stderr_nonzero(self):
        state = done(launch('bash', 'echo expected-error >&2; exit 7'))
        self.assertEqual(state['status'], 'failed')
        self.assertEqual(state['exit_code'], 7)
        self.assertIn('expected-error', state['output'])
    def test_streaming_and_stop(self):
        sid = launch('python', 'import time; print("before-sleep", flush=True); time.sleep(10)')
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            state = request('/commands/' + sid)
            if 'before-sleep' in state['output']: break
            time.sleep(.05)
        self.assertEqual(state['status'], 'running')
        self.assertIn('before-sleep', state['output'])
        request('/commands/' + sid + '/stop', {})
        self.assertEqual(done(sid)['status'], 'cancelled')
    def test_timeout(self):
        self.assertEqual(done(launch('bash', 'sleep 10', 1))['status'], 'timed_out')
    def test_workdir_escape(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            request('/commands', {'engine': 'bash', 'command': 'pwd', 'cwd': '/etc'})
        self.assertEqual(error.exception.code, 400)

if __name__ == '__main__': unittest.main(verbosity=2)
