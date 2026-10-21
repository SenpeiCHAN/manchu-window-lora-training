import { useEffect, useRef, useState } from 'react'
import { Activity, ArrowDownToLine, CheckCircle2, Clock3, Download, FileImage, FileText, LoaderCircle, RefreshCw, Square, Tags, Terminal, TrendingDown, WandSparkles, X } from 'lucide-react'
import { API, api } from '../lib/api'
import { JobSummary, LossChart, LossPoint } from './JobCharts'

type Job = { id: string; kind: string; status: string; progress: number; message: string; current_step?: number; total_steps?: number; created_at: string; started_at?: string; finished_at?: string; error?: string | null }
type Detail = Job & { events: { id: number; event_type: string; payload: {line?: string; message?: string}; created_at: string }[]; artifacts: {id: string; kind: string; path: string}[] }
const label = (value: string) => ({train:'LoRA 训练',tag:'WD14 自动打标',infer:'SD + LoRA 推理',model_download:'模型下载'}[value] || value)
const status = (value: string) => ({queued:'排队中',validating:'校验中',running:'运行中',succeeded:'已完成',failed:'失败',cancelling:'停止中',cancelled:'已停止',interrupted:'已中断'}[value] || value)
const icons = { train: Activity, tag: Tags, infer: WandSparkles, model_download: Download }
const active = ['queued','validating','running','cancelling']

export function JobsPanel({ jobs, onRefresh, onToast }: { jobs: Job[]; onRefresh: () => void; onToast: (message: string) => void }) {
  const [selected, setSelected] = useState<string | null>(null)
  const [filter, setFilter] = useState('all')
  const shown = jobs.filter(j => filter === 'all' || (filter === 'active' ? active.includes(j.status) : filter === 'failed' ? ['failed','interrupted'].includes(j.status) : j.status === filter))
  const cancel = async (id: string) => { try { await api(`/jobs/${id}/cancel`,{method:'POST'}); onToast('已请求停止任务'); onRefresh() } catch(error) { onToast(error instanceof Error ? error.message : '停止失败') } }
  return <><div className="page-intro"><div><span className="eyebrow">任务</span><h2>任务中心</h2><p>查看打标、训练和推理的状态。点击任务按钮打开日志与结果。</p></div><button className="button secondary" onClick={onRefresh}><RefreshCw size={16} />刷新状态</button></div>
    <JobSummary jobs={jobs} />
    <section className="card jobs-card"><div className="filter-tabs" role="group" aria-label="筛选任务">{[['all','全部'],['active','进行中'],['succeeded','已完成'],['failed','失败']].map(([id,text])=><button key={id} className={`filter ${filter===id?'active':''}`} onClick={()=>setFilter(id)}>{text}</button>)}</div>
    {!shown.length && <div className="empty"><Clock3 size={22} /><strong>没有符合条件的任务</strong><span>切换筛选项，或从数据集、训练和推理页提交任务。</span></div>}
    {shown.map(job=>{const Icon=icons[job.kind as keyof typeof icons] || Activity;return <article className="job-detail" key={job.id}><div className="job-row"><span className="job-type"><Icon size={17} /></span><div className="job-info"><strong>{label(job.kind)}</strong><span>{job.message} · {job.id.slice(-6)}</span></div><span className={`status-badge ${job.status}`}>{status(job.status)}</span></div><div className="job-progress"><div className="progress-track" role="progressbar" aria-label={label(job.kind)} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(job.progress*100)}><span style={{width:`${job.progress*100}%`}} /></div><div><span>{job.message}</span><span>{job.current_step && job.total_steps ? `${job.current_step}/${job.total_steps} 步` : `${Math.round(job.progress*100)}%`}</span></div></div>{job.error && <p className="error-text">{job.error}</p>}<div className="job-actions">{active.includes(job.status) && <button className="button danger-ghost" onClick={()=>cancel(job.id)} disabled={job.status==='cancelling'}><Square size={14} />停止</button>}<button className="button ghost" aria-label={`查看过程与结果 ${job.id.slice(-6)}`} onClick={()=>setSelected(job.id)}><Terminal size={15} />查看过程与结果</button></div></article>})}</section>
    {selected && <JobDrawer key={selected} id={selected} onClose={()=>setSelected(null)} />}
  </>
}

function JobDrawer({ id, onClose }: { id: string; onClose: () => void }) {
  const [detail,setDetail]=useState<Detail | null>(null), [points,setPoints]=useState<LossPoint[]>([]), [error,setError]=useState(''), [tab,setTab]=useState('overview'), [tail,setTail]=useState(true), [updated,setUpdated]=useState('')
  const drawer=useRef<HTMLElement>(null), log=useRef<HTMLPreElement>(null), close=useRef(onClose)
  close.current=onClose
  useEffect(()=>{
    let mounted=true, pending=false
    const controller=new AbortController()
    const load=async()=>{
      if(pending)return; pending=true
      try { const job=await api<Detail>(`/jobs/${id}`,{signal:controller.signal}); const metric=job.kind==='train' ? await api<{points:LossPoint[]}>(`/jobs/${id}/metrics`,{signal:controller.signal}) : {points:[]}; if(mounted){setDetail(job);setPoints(metric.points);setError('');setUpdated(new Date().toLocaleTimeString())} }
      catch(e){if(mounted)setError(e instanceof Error?e.message:'任务读取失败')}
      finally{pending=false}
    }
    load();const interval=window.setInterval(load,2000)
    return()=>{mounted=false;controller.abort();window.clearInterval(interval)}
  },[id])
  useEffect(()=>{if(tail && log.current)log.current.scrollTop=log.current.scrollHeight},[detail,tail,tab])
  useEffect(()=>{
    const previous=document.activeElement as HTMLElement|null, overflow=document.body.style.overflow
    document.body.style.overflow='hidden';drawer.current?.focus()
    const key=(event:KeyboardEvent)=>{
      if(event.key==='Escape'){event.preventDefault();close.current()}
      if(event.key==='Tab'){
        const items=Array.from(drawer.current?.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input')||[]),first=items[0],last=items[items.length-1]
        if(event.shiftKey && (document.activeElement===first||document.activeElement===drawer.current)){event.preventDefault();last?.focus()}
        else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus()}
      }
    }
    window.addEventListener('keydown',key)
    return()=>{document.body.style.overflow=overflow;window.removeEventListener('keydown',key);previous?.focus()}
  },[])
  return <div className="drawer-backdrop"><section className="job-drawer" ref={drawer} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="job-drawer-title"><header className="drawer-header"><div><span className="eyebrow">{id}</span><h3 id="job-drawer-title">{detail?label(detail.kind):'任务详情'}</h3></div><button className="icon-button" onClick={onClose} aria-label="关闭任务详情"><X size={20} /></button></header>
    <div className="drawer-tabs" role="group" aria-label="任务详情内容">{[['overview','概况',Activity],['logs','运行日志',Terminal],['results','结果',FileImage],['loss','训练曲线',TrendingDown]].map(([value,text,Icon])=><button key={String(value)} className={tab===value?'selected':''} onClick={()=>setTab(String(value))}>{typeof Icon!=='string'&&<Icon size={15} />}{String(text)}</button>)}</div>
    <div className="drawer-body">{error&&<div className="inline-error" role="alert">读取失败：{error}。每两秒重试；也可关闭后重新打开。</div>}
    {!detail&&!error&&<div className="empty"><LoaderCircle className="spin" size={23} /><strong>正在读取任务…</strong></div>}
    {detail&&<><div className="drawer-status"><span className={`status-badge ${detail.status}`}>{status(detail.status)}</span><span className="muted">更新于 {updated}</span></div>
      {tab==='overview'&&<><div className="detail-metrics"><div><strong>{Math.round(detail.progress*100)}%</strong><span>完成进度</span></div><div><strong>{detail.current_step||'—'} / {detail.total_steps||'—'}</strong><span>执行步数</span></div><div><CheckCircle2 size={20} /><strong>{detail.artifacts.length}</strong><span>产物文件</span></div></div><p className="summary-note">{detail.message}</p>{detail.error&&<p className="inline-error">{detail.error}</p>}<ol className="task-timeline">{[['提交',detail.created_at],['开始',detail.started_at],['结束',detail.finished_at]].map(([name,time])=><li key={name}><Clock3 size={15} /><strong>{name}</strong><span>{time?new Date(time).toLocaleString():'尚未发生'}</span></li>)}</ol>{detail.kind==='train'&&<LossChart points={points} />}</>}
      {tab==='logs'&&<><div className="log-toolbar"><span><Terminal size={15} />任务进程输出 · 最近 200 条</span><label><input type="checkbox" checked={tail} onChange={e=>setTail(e.target.checked)} />跟随最新输出</label></div><pre ref={log} className="console-output">{detail.events.map(e=>`[${new Date(e.created_at).toLocaleTimeString()}] ${e.payload.line||e.payload.message||e.event_type}`).join('\n')||'暂无输出'}</pre></>}
      {tab==='results'&&<>{!detail.artifacts.length&&<div className="empty"><FileImage size={23} /><strong>暂无产物</strong><span>任务完成后显示文件和图片。</span></div>}<div className="result-artifacts">{detail.artifacts.map(a=>a.kind.includes('image')?<figure key={a.id}><figcaption><FileImage size={15} />{a.kind==='base-image'?'基础模型图':'LoRA 图'}</figcaption><img src={`${API}/image?path=${encodeURIComponent(a.path)}`} alt={a.kind==='base-image'?'基础模型图':'LoRA 图'} /><a className="button secondary" href={`${API}/files/download?path=${encodeURIComponent(a.path)}`}><ArrowDownToLine size={15} />下载图片</a></figure>:<div className="artifact" key={a.id}><FileText size={18} /><strong>{a.kind==='lora'?'LoRA 模型':a.kind==='logs'?'运行日志':a.kind}</strong><small>{a.path}</small><a className="button secondary" href={`${API}/files/download?path=${encodeURIComponent(a.path)}`}><ArrowDownToLine size={15} />下载文件</a></div>)}</div></>}
      {tab==='loss'&&<LossChart points={points} />}
    </>}
    </div></section></div>
}
