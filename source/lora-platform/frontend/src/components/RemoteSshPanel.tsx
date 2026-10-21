import { useEffect, useState } from 'react'
import { FolderOpen, Network, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'
import { ConsoleOutput } from './CommandConsole'

type Profile = { provider: 'autodl' | 'other'; host: string; port: number; username: string; workdir: string; fingerprint: string }
const defaults: Profile = { provider: 'autodl', host: '', port: 22, username: 'root', workdir: '/root/autodl-tmp/LoRA', fingerprint: '' }

export function RemoteSshPanel({ onToast }: { onToast: (message: string) => void }) {
  const [profile, setProfile] = useState<Profile>(defaults)
  const [password, setPassword] = useState('')
  const [passphrase, setPassphrase] = useState('')
  const [key, setKey] = useState<File | null>(null)
  const [candidate, setCandidate] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState('')
  const [command, setCommand] = useState('pwd; uname -a; nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv')
  const [session, setSession] = useState<string | null>(null)
  useEffect(() => { api<Profile>('/remote/ssh/config').then(setProfile).catch(() => onToast('读取 SSH 配置失败')) }, [onToast])
  const update = (values: Partial<Profile>) => {
    setProfile(previous => ({ ...previous, ...values, ...('host' in values || 'port' in values ? { fingerprint: '' } : {}) }))
    if ('host' in values || 'port' in values) setCandidate('')
    setResult('')
  }
  const run = async (action: () => Promise<void>) => {
    setBusy(true)
    try { await action() } catch (error) { onToast(error instanceof Error ? error.message : 'SSH 操作失败') } finally { setBusy(false) }
  }
  const probe = () => run(async () => {
    const response = await api<{ fingerprint: string }>('/remote/ssh/probe', { method: 'POST', body: JSON.stringify(profile) })
    setCandidate(response.fingerprint)
    setResult('请与服务器提供的指纹核对，然后点击确认。')
  })
  const save = () => run(async () => {
    await api('/remote/ssh/config', { method: 'PUT', body: JSON.stringify(profile) })
    onToast('SSH 配置已保存；密码和私钥不会保存。')
  })
  const test = () => run(async () => {
    const data = new FormData()
    data.append('profile', JSON.stringify(profile)); data.append('password', password); data.append('passphrase', passphrase)
    if (key) data.append('private_key', key)
    try {
      const response = await api<{ message: string; workdir_exists: boolean | null }>('/remote/ssh/test', { method: 'POST', body: data })
      setResult(`${response.message} ${response.workdir_exists ? '工作目录可访问。' : '工作目录未确认，请核实路径。'}`)
    } finally { setPassword(''); setPassphrase(''); setKey(null) }
  })
  const execute = () => run(async () => {
    const data = new FormData()
    data.append('profile', JSON.stringify(profile)); data.append('password', password); data.append('passphrase', passphrase); data.append('command', command)
    if (key) data.append('private_key', key)
    try { const response = await api<{id:string}>('/remote/ssh/command', {method:'POST',body:data}); setSession(response.id) }
    finally { setPassword(''); setPassphrase(''); setKey(null) }
  })
  return <section className="card remote-card">
    <div className="section-title"><div><span className="eyebrow">远程扩展</span><h3>SSH 服务器</h3></div><Network size={18} /></div>
    <p className="muted">支持 AutoDL 或其他 SSH 服务器。可保存连接配置、验证指纹和测试登录；远程训练调度接口预留，当前任务仍在本机运行。</p>
    <fieldset disabled={busy} className="ssh-fields"><div className="form-grid">
      <label>服务器类型<select value={profile.provider} onChange={e => update({ provider: e.target.value as Profile['provider'] })}><option value="autodl">AutoDL</option><option value="other">其他服务器</option></select></label>
      <label>服务器地址<input value={profile.host} placeholder="服务器域名或 IP" onChange={e => update({ host: e.target.value })} /></label>
      <label>SSH 端口<input type="number" min="1" max="65535" value={profile.port} onChange={e => update({ port: Number(e.target.value) })} /></label>
      <label>用户名<input value={profile.username} onChange={e => update({ username: e.target.value })} /></label>
      <label className="wide">远程工作目录<input value={profile.workdir} onChange={e => update({ workdir: e.target.value })} /></label>
      <label>登录密码（仅本次）<input type="password" autoComplete="off" value={password} onChange={e => setPassword(e.target.value)} /></label>
      <label>私钥口令（可选，仅本次）<input type="password" autoComplete="off" value={passphrase} onChange={e => setPassphrase(e.target.value)} /></label>
      <label className="wide">或选择本地私钥文件<input key={key?.name || 'empty'} type="file" onChange={e => setKey(e.target.files?.[0] || null)} /><small>通过文件选择窗口上传，仅用于本次验证，平台不保存私钥。</small></label>
    </div></fieldset>
    {(candidate || profile.fingerprint) && <div className="path-current">{candidate || profile.fingerprint}{candidate && candidate !== profile.fingerprint && <button className="text-button" disabled={busy} onClick={() => { update({ fingerprint: candidate }); setCandidate('') }}>确认此指纹</button>}</div>}
    <div className="job-actions"><button className="button secondary" disabled={busy || !profile.host} onClick={probe}><RefreshCw size={15} />获取指纹</button><button className="button secondary" disabled={busy} onClick={save}><FolderOpen size={15} />保存配置</button><button className="button primary" disabled={busy || !profile.fingerprint || (!password && !key)} onClick={test}>{busy ? '连接中…' : '测试 SSH 登录'}</button></div>
    {result && <p className="summary-note" role="status">{result}</p>}
    <label>服务器命令<textarea rows={3} value={command} onChange={e=>setCommand(e.target.value)} spellCheck={false}/></label>
    <p className="muted">执行位置：上方 SSH 服务器。填写本次凭据后执行，返回内容会显示在这里。此处命令不进入本机 GPU 队列。</p>
    <div className="job-actions"><button className="button primary" disabled={busy||!profile.fingerprint||(!password&&!key)||!command.trim()} onClick={execute}>连接并执行</button></div>
    <ConsoleOutput id={session}/>
  </section>
}
