import { BarChart3, Clock3, TrendingDown } from 'lucide-react'

export type LossPoint = { step: number; total: number; loss: number; created_at: string }
export function LossChart({ points }: { points: LossPoint[] }) {
  if (!points.length) return <div className="chart-empty"><TrendingDown size={22} /><strong>暂无损失数据</strong><span>训练产生平均损失后，这里会显示曲线。</span></div>
  const width = 560, height = 210, left = 60, right = 22, top = 22, bottom = 40
  const xMin = Math.min(...points.map(p => p.step)), xMax = Math.max(...points.map(p => p.step))
  const low = Math.min(...points.map(p => p.loss)), high = Math.max(...points.map(p => p.loss))
  const pad = Math.max((high - low) * .15, Math.abs(high) * .1, .00001)
  const yMin = Math.max(0, low - pad), yMax = high + pad
  const x = (step: number) => left + (xMax === xMin ? .5 : (step - xMin) / (xMax - xMin)) * (width - left - right)
  const y = (loss: number) => top + (1 - (loss - yMin) / (yMax - yMin)) * (height - top - bottom)
  return <div className="loss-chart"><div className="chart-heading"><TrendingDown size={17} /><strong>平均训练损失</strong><span>最新 {points[points.length - 1].loss.toPrecision(4)}</span></div><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`平均训练损失，${points.length} 个采样点，步数 ${xMin} 到 ${xMax}`}>
    {[0, .5, 1].map(r => { const value = yMin + (yMax - yMin) * r; return <g key={r}><line x1={left} y1={y(value)} x2={width - right} y2={y(value)} className="chart-grid" /><text x={left - 9} y={y(value) + 4} textAnchor="end">{value.toPrecision(3)}</text></g> })}
    <polyline points={points.map(p => `${x(p.step)},${y(p.loss)}`).join(' ')} fill="none" className="chart-line" />
    {points.map(p => <circle key={p.step} cx={x(p.step)} cy={y(p.loss)} r="3" className="chart-point"><title>{`第 ${p.step} 步 · 平均损失 ${p.loss}`}</title></circle>)}
    <text x={left} y={height - 10}>{xMin} 步</text>{xMax !== xMin && <text x={width - right} y={height - 10} textAnchor="end">{xMax} 步</text>}
  </svg><p className="muted">来自 sd-scripts 日志。只有一个点时显示单点，不补齐曲线。</p></div>
}

export function JobSummary({ jobs }: { jobs: { status: string; kind: string; started_at?: string; finished_at?: string }[] }) {
  const groups = [{label:'已完成',status:['succeeded'],tone:'success'}, {label:'进行中',status:['running','validating','cancelling'],tone:'active'}, {label:'排队中',status:['queued'],tone:'neutral'}, {label:'失败／已停止',status:['failed','cancelled','interrupted'],tone:'danger'}]
  const rows = groups.map(g => ({...g,count:jobs.filter(j => g.status.includes(j.status)).length}))
  const durations = jobs.filter(j => j.started_at && j.finished_at && j.status === 'succeeded').slice(0,5).map(j => ({label:j.kind === 'train' ? '训练' : j.kind === 'tag' ? 'WD14' : j.kind === 'infer' ? '推理' : '下载',seconds:Math.max(0,(Date.parse(j.finished_at!) - Date.parse(j.started_at!))/1000)}))
  const max = Math.max(1,...durations.map(d=>d.seconds))
  return <div className="job-summary"><section className="card"><div className="chart-heading"><BarChart3 size={17} /><strong>任务状态</strong><span>当前列表 {jobs.length} 项</span></div><div className="status-distribution" aria-label="当前任务状态分布">{rows.filter(r=>r.count).map(r=><span key={r.label} className={r.tone} style={{width:`${r.count/Math.max(jobs.length,1)*100}%`}} title={`${r.label} ${r.count}`} />)}</div><div className="chart-legend">{rows.map(r=><span key={r.label}><i className={r.tone} />{r.label}<strong>{r.count}</strong></span>)}</div></section><section className="card"><div className="chart-heading"><Clock3 size={17} /><strong>最近完成任务耗时</strong></div>{durations.length ? <div className="duration-bars">{durations.map((d,i)=><div key={i}><span>{d.label}</span><div><i style={{width:`${Math.max(1,d.seconds/max*100)}%`}} /></div><span>{d.seconds < 60 ? `${d.seconds.toFixed(1)} 秒` : `${(d.seconds/60).toFixed(1)} 分`}</span></div>)}</div> : <p className="muted">任务完成后显示耗时。</p>}</section></div>
}
