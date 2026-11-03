import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowRight, Eye, EyeOff, ShieldCheck } from 'lucide-react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/auth'
import { Field, Notice } from '../components/ui'
import { AuthorSignature, Brand, TimeDial } from '../components/identity'

const schema = z.object({ organization: z.string().trim().min(1, 'Informe sua organização.'), username: z.string().trim().min(1, 'Informe seu usuário.'), password: z.string().min(1, 'Informe sua senha.') })

export function LoginPage() {
  const { user, login, message } = useAuth()
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const { register, handleSubmit, resetField, formState: { errors, isSubmitting } } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { organization: 'horizonte', username: '', password: '' } })
  if (user) return <Navigate to="/" replace />

  return <div className="login-page">
    <section className="login-story" aria-labelledby="story-title">
      <a className="brand" href="/" aria-label="Chronos 1.0"><Brand /></a>
      <div className="story-copy">
        <p className="eyebrow"><span className="edition-index">01 /</span> PESSOAS. TEMPO. POSSIBILIDADES.</p>
        <h1 id="story-title">O tempo encontra<br />seu <em>equilíbrio.</em></h1>
        <p>Por trás de cada jornada, uma pessoa.<br />À frente de cada decisão, uma nova possibilidade.</p>
      </div>
      <TimeDial />
      <div className="story-footer"><AuthorSignature /><span>CHRONOS 1.0<br /><b>Feito para conectar.</b></span></div>
    </section>
    <main className="login-main">
      <div className="login-card">
        <span className="login-label"><span className="status-dot" /> SEU ESPAÇO DE PLANEJAMENTO</span>
        <p className="login-step">ACESSO / 01</p>
        <h2>Bom ter você<br /> por aqui<span className="brand-period">.</span></h2>
        <p className="subtitle">Entre para cuidar do que move sua operação.</p>
        {(error || message) && <Notice error>{error || message}</Notice>}
        <form onSubmit={handleSubmit(async values => {
          setError('')
          try { await login(values.organization, values.username, values.password) }
          catch (err) { setError((err as Error).message); resetField('password'); setShowPassword(false) }
        })}>
          <Field label="Organização" error={errors.organization?.message}><input {...register('organization')} autoComplete="organization" aria-invalid={!!errors.organization} /></Field>
          <Field label="Usuário" error={errors.username?.message}><input {...register('username')} autoComplete="username" aria-invalid={!!errors.username} /></Field>
          <div className="password-field"><Field label="Senha" error={errors.password?.message}><input {...register('password')} type={showPassword ? 'text' : 'password'} autoComplete="current-password" aria-invalid={!!errors.password} /></Field><button className="password-toggle icon-button" type="button" aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>
          <button className="button primary login-submit" disabled={isSubmitting}>{isSubmitting ? 'Entrando…' : 'Entrar na plataforma'}<ArrowRight size={18} /></button>
        </form>
        <div className="login-footnote"><ShieldCheck size={17} /><span>Ambiente de demonstração<br /><b>Dados fictícios. Possibilidades reais de explorar.</b></span></div>
      </div>
      <div className="login-mobile-signature"><AuthorSignature /></div>
      <p className="login-copyright">Chronos 1.0 — Gestão Inteligente de Jornadas e Escalas</p>
    </main>
  </div>
}
