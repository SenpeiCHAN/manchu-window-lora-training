"""Verify multipart SSH API and shared polling session against loopback fixture."""
import json
import time
import urllib.request

BASE = 'http://127.0.0.1:8000/api'
profile = {'host': '127.0.0.1', 'port': 22222, 'username': 'root', 'workdir': '/tmp', 'provider': 'other'}
def request(path, payload=None, headers=None):
    with urllib.request.urlopen(urllib.request.Request(BASE+path, data=payload, headers=headers or {}), timeout=12) as response:
        return json.load(response)

profile['fingerprint'] = request('/remote/ssh/probe', json.dumps(profile).encode(), {'Content-Type':'application/json'})['fingerprint']
boundary = 'lora-test-multipart-boundary'
fields = {'profile':json.dumps(profile),'command':'pwd; printf "SSH HTTP acceptance OK\\n"; printf "stderr visible\\n" >&2','password':'test-only-password','timeout':'5'}
payload = ''.join(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n' for name,value in fields.items()) + f'--{boundary}--\r\n'
sid = request('/remote/ssh/command',payload.encode(),{'Content-Type':f'multipart/form-data; boundary={boundary}'})['id']
deadline = time.monotonic()+12
while time.monotonic()<deadline:
    state = request('/terminal/commands/'+sid)
    if state['status'] != 'running': break
    time.sleep(.08)
assert state['status']=='succeeded', state
assert state['exit_code']==0, state
assert 'SSH HTTP acceptance OK' in state['output'] and 'stderr visible' in state['output'] and '/tmp' in state['output'], state
print(json.dumps(state,ensure_ascii=False,indent=2))
print('PASS: fingerprint, multipart authentication, stdout/stderr, session polling, exit code')
