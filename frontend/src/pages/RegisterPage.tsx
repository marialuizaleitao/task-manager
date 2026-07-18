import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { extractFieldErrors } from '../services/api'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

interface FieldErrors {
  email?: string
  password?: string
  password_confirm?: string
  non_field_errors?: string
}

function validateEmail(value: string): string | undefined {
  if (!value.trim()) return 'Informe seu e-mail.'
  if (!EMAIL_PATTERN.test(value)) return 'Informe um e-mail válido.'
  return undefined
}

function validatePasswordValue(value: string): string | undefined {
  if (!value) return 'Informe uma senha.'
  if (value.length < 8) return 'A senha deve ter pelo menos 8 caracteres.'
  return undefined
}

function validateConfirm(password: string, confirm: string): string | undefined {
  if (!confirm) return 'Confirme sua senha.'
  if (confirm !== password) return 'As senhas não coincidem.'
  return undefined
}

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const passwordsMatch = passwordConfirm.length > 0 && passwordConfirm === password

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()

    const errors: FieldErrors = {
      email: validateEmail(email),
      password: validatePasswordValue(password),
      password_confirm: validateConfirm(password, passwordConfirm),
    }
    setFieldErrors(errors)
    if (errors.email || errors.password || errors.password_confirm) return

    setIsSubmitting(true)
    try {
      await register({
        email,
        password,
        password_confirm: passwordConfirm,
        first_name: firstName,
        last_name: lastName,
      })
      navigate('/')
    } catch (err) {
      setFieldErrors(extractFieldErrors(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-card">
        <h1>Criar conta</h1>
        <form onSubmit={handleSubmit} noValidate>
          <div className="field-row">
            <label>
              Nome
              <input value={firstName} onChange={(event) => setFirstName(event.target.value)} />
            </label>
            <label>
              Sobrenome
              <input value={lastName} onChange={(event) => setLastName(event.target.value)} />
            </label>
          </div>
          <label>
            E-mail <span className="required-marker">*</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              onBlur={() => setFieldErrors((current) => ({ ...current, email: validateEmail(email) }))}
            />
            {fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}
          </label>
          <label>
            Senha <span className="required-marker">*</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              onBlur={() =>
                setFieldErrors((current) => ({ ...current, password: validatePasswordValue(password) }))
              }
            />
            {fieldErrors.password ? (
              <span className="field-error">{fieldErrors.password}</span>
            ) : (
              <span className="field-hint">Mínimo de 8 caracteres. Evite senhas óbvias ou apenas números.</span>
            )}
          </label>
          <label>
            Confirmar senha <span className="required-marker">*</span>
            <input
              type="password"
              value={passwordConfirm}
              onChange={(event) => setPasswordConfirm(event.target.value)}
              onBlur={() =>
                setFieldErrors((current) => ({
                  ...current,
                  password_confirm: validateConfirm(password, passwordConfirm),
                }))
              }
            />
            {fieldErrors.password_confirm ? (
              <span className="field-error">{fieldErrors.password_confirm}</span>
            ) : (
              passwordsMatch && <span className="field-success">As senhas coincidem.</span>
            )}
          </label>
          {fieldErrors.non_field_errors && <p className="error">{fieldErrors.non_field_errors}</p>}
          <button type="submit" className={isSubmitting ? 'btn-loading' : undefined} disabled={isSubmitting}>
            {isSubmitting ? 'Criando conta...' : 'Criar conta'}
          </button>
        </form>
        <p className="auth-switch">
          Já tem conta? <Link to="/login">Entrar</Link>
        </p>
      </div>
    </main>
  )
}
