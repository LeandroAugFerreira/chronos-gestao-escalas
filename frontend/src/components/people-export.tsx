import { useRef, useState } from 'react'
import { Download } from 'lucide-react'
import { api } from '../services/client'
import { saveFile, type DownloadFile } from '../services/download'
import { useAuth } from '../hooks/auth'
import { permits } from '../types/domain'
import { Failure } from './ui'

type Selection = { search: string; unit_id: string; department_id: string; status: string; sort: string }
type PeopleFile = DownloadFile & { row_count: number }

export function PeopleExport({ selection }: { selection: Selection }) {
  const { user } = useAuth()
  const [pending, setPending] = useState(false); const busy = useRef(false)
  const [error, setError] = useState<Error | null>(null); const [notice, setNotice] = useState('')
  if (!permits(user, 'people:read', selection.unit_id || undefined)) return null
  async function download() {
    if (busy.current) return
    busy.current = true; setPending(true); setError(null); setNotice('')
    const { unit_id, department_id, status, ...fields } = selection
    try {
      const file = await api.send<PeopleFile>('/employees/export', 'POST', { ...fields, unit_id: unit_id || null, department_id: department_id || null, status: status || null })
      await saveFile(file)
      setNotice(`${file.row_count} colaboradores no arquivo verificado: ${file.filename}. O conteúdo corresponde aos filtros no momento da solicitação.`)
    } catch (e) { setError(e instanceof Error ? e : new Error('Não foi possível exportar os colaboradores.')) }
    finally { busy.current = false; setPending(false) }
  }
  return <section className="panel" aria-label="Exportação cadastral">
    <div className="panel-title"><h2>Exportar colaboradores</h2><button className="button secondary" disabled={pending} onClick={() => void download()}><Download size={16} />{pending ? 'Preparando CSV…' : 'Exportar CSV'}</button></div>
    <p className="muted">Inclui todas as páginas dos filtros selecionados e apenas as unidades autorizadas. Até 20.000 registros e 8 MiB, sem salários, contratos, evidências ou ausências. IDs de unidade, setor e função permitem relacionar os cadastros.</p>
    <p className="form-note">Texto com início de fórmula recebe apóstrofo de proteção. Importe IDs e matrícula como texto. O arquivo baixado não mantém as permissões do Chronos; proteja seu armazenamento.</p>
    {notice && <p role="status">{notice}</p>}{error && <Failure error={error} />}
  </section>
}
