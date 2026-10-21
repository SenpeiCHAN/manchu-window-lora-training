import { useCallback, useEffect, useRef, useState } from 'react'
import { FolderOpen } from 'lucide-react'
import { api } from '../lib/api'

type DirectoryListing = { current: string; parent: string | null; directories: { name: string; path: string }[] }

export function PathPicker({ initial, onSelect, onClose }: { initial: string; onSelect: (path: string) => void; onClose: () => void }) {
  const [listing, setListing] = useState<DirectoryListing | null>(null)
  const [current, setCurrent] = useState(initial.startsWith('/data') ? initial : '/data')
  const [error, setError] = useState('')
  const modal = useRef<HTMLElement>(null)
  const close = useRef(onClose)
  close.current = onClose
  const load = useCallback(async (path: string) => {
    try { setListing(await api<DirectoryListing>(`/browse?path=${encodeURIComponent(path)}`)); setError('') }
    catch { setListing(null); setError('目录读取失败，请返回上一级或重新选择。') }
  }, [])
  useEffect(() => { load(current) }, [current, load])
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    modal.current?.focus()
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); close.current(); return }
      if (event.key !== 'Tab') return
      const targets = Array.from(modal.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') || [])
      const first = targets[0], last = targets[targets.length - 1]
      if (!first) return
      if (event.shiftKey && (document.activeElement === first || document.activeElement === modal.current)) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    window.addEventListener('keydown', keydown)
    return () => { window.removeEventListener('keydown', keydown); document.body.style.overflow = previousOverflow; previous?.focus() }
  }, [])
  return <div className="modal-backdrop"><section className="path-modal" ref={modal} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="path-picker-title">
    <div className="section-title"><div><span className="eyebrow">项目目录选择</span><h3 id="path-picker-title">选择容器内路径</h3></div><button className="text-button" onClick={onClose}>关闭</button></div>
    <p className="muted">/data/manzhou 对应 E:\LoRA-Manzhou；/data/runs/manzhou 和 /data/outputs/lora-platform/manzhou 分别对应其 runs 与 outputs 子目录。其他目录使用 D:\LoRA\data。只能选择已挂载的目录。</p>
    <div className="path-current">{current}</div>
    {error && <p className="error-text" role="alert">{error}</p>}
    <div className="path-items">{listing?.parent && <button onClick={() => setCurrent(listing.parent!)}>.. 上一级</button>}{listing?.directories.map(directory => <button key={directory.path} onClick={() => setCurrent(directory.path)}><FolderOpen size={15} /><span>{directory.name}</span></button>)}</div>
    <div className="job-actions"><button className="button secondary" onClick={onClose}>取消</button><button className="button primary" disabled={!listing} onClick={() => { onSelect(listing!.current); onClose() }}>选择当前目录</button></div>
  </section></div>
}

