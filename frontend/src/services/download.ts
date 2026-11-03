export type DownloadFile = { filename: string; content_type: string; content: string; sha256: string; byte_length: number }

export async function saveFile(file: DownloadFile) {
  const bytes = Uint8Array.from(atob(file.content), char => char.charCodeAt(0))
  const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), value => value.toString(16).padStart(2, '0')).join('')
  if (bytes.length !== file.byte_length || digest !== file.sha256) throw new Error('O arquivo recebido falhou na verificação de integridade.')
  const url = URL.createObjectURL(new Blob([bytes], { type: file.content_type }))
  const link = document.createElement('a'); link.href = url; link.download = file.filename
  document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}
