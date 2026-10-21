import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, FolderOpen, Play, Square, Terminal, TriangleAlert } from 'lucide-react'
import { api } from '../lib/api'
import { PathPicker } from './PathPicker'

type Session = { id: string; engine: string; status: string; output: string; exit_code: number | null }
export function ConsoleOutput({ id }: { id: string | null }) {
  const [session, setSession] = useState<Session | null>(null), [error,setError]=useState(''), [tail,setTail]=useState(true)
  const output=useRef<HTMLPreElement>(null)
  useEffect(()=>{
    if(!id){setSession(null);return}
    let alive=true,pending=false
    setSession(null);setError('')
    const controller=new AbortController()
    const load=async()=>{if(pending)return;pending=true;try{const result=await api<Session>(`/terminal/commands/${id}`,{signal:controller.signal});if(alive){setSession(result);setError('')}}catch(e){if(alive)setError(e instanceof Error?e.message:'输出读取失败')}finally{pending=false}}
    load();const timer=window.setInterval(load,600)
    return()=>{alive=false;controller.abort();window.clearInterval(timer)}
  },[id])
  useEffect(()=>{if(tail&&output.current)output.current.scrollTop=output.current.scrollHeight},[session,tail])
  const stop=async()=>{try{await api(`/terminal/commands/${id}/stop`,{method:'POST'})}catch(e){setError(e instanceof Error?e.message:'停止失败')}}
  return <div className="console-box"><div className="log-toolbar"><span><Terminal size={15} />{session?({running:'运行中',succeeded:'已完成',failed:'执行失败',cancelled:'已停止',timed_out:'超时'}[session.status]||session.status):id?'正在读取输出…':'未执行命令'}</span><label><input type="checkbox" checked={tail} onChange={e=>setTail(e.target.checked)} />跟随输出</label>{session?.status==='running'&&<button className="button danger-ghost" onClick={stop}><Square size={13} />停止</button>}</div>{error&&<p className="inline-error" role="alert">{error}</p>}<pre ref={output} className="console-output" aria-label="终端输出">{session?.output||'输出会显示在这里。'}</pre>{session&&session.status!=='running'&&<p className="console-exit">{session.exit_code===0?<CheckCircle2 size={15}/>:<TriangleAlert size={15}/>}退出码 {session.exit_code} · 记录在服务重启后或结束十五分钟后清除</p>}</div>
}

export function LocalConsole({onToast}:{onToast:(message:string)=>void}) {
  const [engine,setEngine]=useState('powershell'),[command,setCommand]=useState('$PSVersionTable.PSVersion; Get-Location'),[cwd,setCwd]=useState('/data'),[session,setSession]=useState<string|null>(null),[picker,setPicker]=useState(false),[busy,setBusy]=useState(false)
  const [available,setAvailable]=useState<Record<string,boolean>>({})
  useEffect(()=>{api<{engines:{id:string;available:boolean}[]}>('/terminal/capabilities').then(r=>setAvailable(Object.fromEntries(r.engines.map(e=>[e.id,e.available])))).catch(()=>onToast('无法读取终端环境'))},[onToast])
  const run=async()=>{setBusy(true);try{const r=await api<{id:string}>('/terminal/commands',{method:'POST',body:JSON.stringify({engine,command,cwd,timeout:120})});setSession(r.id)}catch(e){onToast(e instanceof Error?e.message:'命令执行失败')}finally{setBusy(false)}}
  return <section className="card remote-card"><div className="section-title"><div><span className="eyebrow">运行控制</span><h3>容器终端</h3></div><Terminal size={18}/></div><p className="muted">执行位置：API 容器（Linux），项目目录为 /data。支持 PowerShell、Bash 和 Python；输出、错误和退出码显示在下方。命令最多运行两分钟，非交互命令模式。</p><div className="form-grid"><label>执行环境<select value={engine} onChange={e=>{setEngine(e.target.value);setCommand(e.target.value==='powershell'?'$PSVersionTable.PSVersion; Get-Location':e.target.value==='python'?'import sys, os\nprint(sys.version)\nprint(os.getcwd())':'pwd; uname -a')}}>{[['powershell','PowerShell（Linux）'],['bash','Bash'],['python','Python']].map(([id,text])=><option key={id} value={id} disabled={!available[id]}>{text}{available[id]?'':' · 未就绪'}</option>)}</select></label><label>工作目录<div className="picker-row"><input value={cwd} onChange={e=>setCwd(e.target.value)}/><button className="button secondary" onClick={()=>setPicker(true)}><FolderOpen size={15}/>选择</button></div></label></div><label>命令<textarea rows={4} value={command} onChange={e=>setCommand(e.target.value)} spellCheck={false}/></label><div className="job-actions"><button className="button primary" disabled={busy||!command.trim()||!available[engine]} onClick={run}><Play size={15}/>{busy?'正在提交…':'执行命令'}</button></div><ConsoleOutput id={session}/>{picker&&<PathPicker initial={cwd} onSelect={setCwd} onClose={()=>setPicker(false)}/>}</section>
}

