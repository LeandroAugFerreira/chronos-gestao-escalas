/** Elementos vetoriais da identidade Chronos. Funcionam também sem conexão. */
export function ChronosMark({ className = '' }: { className?: string }) {
  return <svg className={'chronos-mark ' + className} viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <path d="M37.9 10.1A19.6 19.6 0 1 0 37.9 37.9" stroke="currentColor" strokeWidth="2.2" />
    <path d="M32.5 15.5A12 12 0 1 0 32.5 32.5" stroke="currentColor" strokeWidth="1.2" opacity=".45" />
    <path d="M24 11.5V24L36 28" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    <circle cx="24" cy="24" r="2.5" fill="currentColor" />
    <path d="M24 2V5M2 24H5M24 43V46M43 24H46" stroke="currentColor" strokeWidth="1.2" />
  </svg>
}

export function Brand({ compact = false }: { compact?: boolean }) {
  return <><ChronosMark /><span className="brand-wordmark">chronos<span className="brand-period">.</span><small>{compact ? 'JORNADAS EM EQUILÍBRIO' : 'GESTÃO INTELIGENTE DE JORNADAS E ESCALAS'}</small></span></>
}

export function AuthorSignature() {
  return <div className="author-signature"><span className="author-monogram" aria-hidden="true">lf<span>.</span></span><span><small>DESIGN & DESENVOLVIMENTO</small><b>Leandro Augusto Ferreira</b></span></div>
}

export function TimeDial() {
  return <div className="time-dial" aria-hidden="true"><svg viewBox="0 0 440 440" fill="none">
    <circle cx="220" cy="220" r="204" stroke="currentColor" opacity=".16" />
    <circle cx="220" cy="220" r="179" stroke="currentColor" opacity=".24" />
    <circle cx="220" cy="220" r="133" stroke="currentColor" opacity=".13" />
    <circle cx="220" cy="220" r="74" stroke="currentColor" strokeDasharray="1 7" opacity=".35" />
    {Array.from({ length: 60 }, (_, n) => <line key={n} x1="220" y1={n % 5 === 0 ? '48' : '54'} x2="220" y2="62" transform={`rotate(${n * 6} 220 220)`} stroke="currentColor" strokeWidth={n % 5 === 0 ? 2 : 1} opacity={n % 5 === 0 ? .7 : .3} />)}
    <path d="M220 87A133 133 0 0 1 353 220" stroke="currentColor" strokeWidth="5" />
    <path d="M220 220L156 147M220 220L322 180" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    <circle cx="220" cy="220" r="6" fill="currentColor" />
    <path d="M12 220H33M407 220H428M220 12V33M220 407V428" stroke="currentColor" />
    <text x="220" y="112" textAnchor="middle">CHRONOS</text>
    <text x="220" y="311" textAnchor="middle">PESSOAS & TEMPO</text>
  </svg><span className="dial-caption">CADA HORA TEM SEU VALOR.</span></div>
}

/** Motivo gráfico da marca: uma linha do tempo, sem representar uma escala real. */
export function RhythmMotif() {
  return <div className="rhythm-motif" aria-hidden="true"><div className="rhythm-hours"><span>00</span><span>06</span><span>12</span><span>18</span><span>24</span></div><div className="rhythm-lines"><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /></div><span>PESSOAS · JORNADAS · DECISÕES</span></div>
}
