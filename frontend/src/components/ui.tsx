import { cloneElement, isValidElement, useEffect, useId, useRef, type ReactElement, type ReactNode } from 'react'
import { AlertCircle, CheckCircle2, ChevronLeft, ChevronRight, LoaderCircle, X } from 'lucide-react'

export function Notice({ children, error = false }: { children: ReactNode; error?: boolean }) { return <div className={'notice ' + (error ? 'error' : '')} role={error ? 'alert' : 'status'}>{error ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}<div>{children}</div></div> }
export function Loading() { return <div className="loading" role="status"><LoaderCircle className="spin" size={22} />Carregando dados…</div> }
export function Failure({ error, retry }: { error: Error; retry?: () => void }) { return <Notice error><p>{error.message}</p>{retry && <button className="text-button" onClick={retry}>Tentar novamente</button>}</Notice> }
export function Empty({ children }: { children: ReactNode }) { return <div className="empty">{children}</div> }
export function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) { return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1>{description && <p className="subtitle">{description}</p>}</div>{action}</div> }
export function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  const id = useId()
  const input = isValidElement(children) ? cloneElement(children as ReactElement<Record<string, unknown>>, { id, 'aria-invalid': !!error, 'aria-describedby': error ? id + '-error' : undefined }) : children
  return <div className="field"><label htmlFor={id}>{label}</label>{input}{error && <small id={id + '-error'} className="field-error" role="alert">{error}</small>}</div>
}
export function Submit({ pending, children = 'Salvar alterações' }: { pending: boolean; children?: ReactNode }) { return <button type="submit" className="button primary" disabled={pending}>{pending && <LoaderCircle size={16} className="spin" />}{pending ? 'Salvando…' : children}</button> }
export function Modal({ title, children, onClose, pending = false }: { title: string; children: ReactNode; onClose: () => void; pending?: boolean }) {
  const id = useId()
  const container = useRef<HTMLDivElement>(null)
  const pendingRef = useRef(pending)
  pendingRef.current = pending
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const root = container.current!
    const focusable = () => Array.from(root.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]')).filter(node => node.tabIndex !== -1)
    focusable()[0]?.focus()
    function key(event: KeyboardEvent) {
      if (event.key === 'Escape' && !pendingRef.current) { event.preventDefault(); onClose() }
      if (event.key === 'Tab') {
        const nodes = focusable(); const first = nodes[0]; const last = nodes[nodes.length - 1]
        if (nodes.length === 0) { event.preventDefault(); root.focus(); return }
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
      }
    }
    document.addEventListener('keydown', key)
    return () => { document.removeEventListener('keydown', key); document.body.style.overflow = previousOverflow; before?.focus() }
  }, [onClose])
  return <div className="modal-backdrop"><div className="modal" role="dialog" aria-modal="true" aria-labelledby={id} ref={container} tabIndex={-1}><div className="modal-heading"><h2 id={id}>{title}</h2><button className="icon-button" onClick={onClose} disabled={pending} aria-label="Fechar formulário"><X size={20} /></button></div>{children}</div></div>
}
export function Pagination({ page, total, size, setPage }: { page: number; total: number; size: number; setPage: (page: number) => void }) { const pages = Math.max(1, Math.ceil(total / size)); return <div className="pagination"><span>{total} registros · página {page} de {pages}</span><div><button className="icon-button" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Página anterior"><ChevronLeft size={18} /></button><button className="icon-button" disabled={page >= pages} onClick={() => setPage(page + 1)} aria-label="Próxima página"><ChevronRight size={18} /></button></div></div> }
export function dateTime(value: string, timezone = 'America/Sao_Paulo') { return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: timezone }).format(new Date(value)) }
