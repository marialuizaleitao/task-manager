import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

interface FieldErrors {
  email?: string
  password?: string
}

function validateEmail(value: string): string | undefined {
  if (!value.trim()) return 'Informe seu e-mail.'
  if (!EMAIL_PATTERN.test(value)) return 'Informe um e-mail válido.'
  return undefined
}

function validatePassword(value: string): string | undefined {
  if (!value) return 'Informe sua senha.'
  return undefined
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  function handleEmailBlur() {
    setFieldErrors((current) => ({ ...current, email: validateEmail(email) }))
  }

  function handlePasswordBlur() {
    setFieldErrors((current) => ({ ...current, password: validatePassword(password) }))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()

    const emailError = validateEmail(email)
    const passwordError = validatePassword(password)
    setFieldErrors({ email: emailError, password: passwordError })
    if (emailError || passwordError) return

    setError(null)
    setIsSubmitting(true)

    try {
      await login(email, password)
      navigate('/')
    } catch {
      setError('E-mail ou senha inválidos.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-card">
        <h1>Entrar</h1>
        <form onSubmit={handleSubmit} noValidate>
          <label>
            E-mail
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              onBlur={handleEmailBlur}
              autoFocus
            />
            {fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}
          </label>
          <label>
            Senha
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              onBlur={handlePasswordBlur}
            />
            {fieldErrors.password && <span className="field-error">{fieldErrors.password}</span>}
          </label>
          {error && <p className="error">{error}</p>}
          <button type="submit" className={isSubmitting ? 'btn-loading' : undefined} disabled={isSubmitting}>
            {isSubmitting ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
        <p className="auth-switch">
          Não tem conta? <Link to="/register">Cadastre-se</Link>
        </p>
      </div>
    </main>
  )
}
