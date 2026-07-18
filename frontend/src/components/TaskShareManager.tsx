import { useEffect, useState, type FormEvent } from 'react'
import { extractFieldErrors } from '../services/api'
import * as sharingService from '../services/sharing'
import type { SharePermission, TaskShare } from '../services/sharing'

interface TaskShareManagerProps {
  taskId: number
}

interface FieldErrors {
  email?: string
  non_field_errors?: string
}

export function TaskShareManager({ taskId }: TaskShareManagerProps) {
  const [shares, setShares] = useState<TaskShare[]>([])
  const [email, setEmail] = useState('')
  const [permission, setPermission] = useState<SharePermission>('read')
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function loadShares() {
    setIsLoading(true)
    try {
      const data = await sharingService.listTaskShares(taskId)
      setShares(data)
    } catch {
      setLoadError('Não foi possível carregar os compartilhamentos.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadShares()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()

    if (!email.trim()) {
      setFieldErrors({ email: 'Informe o e-mail de quem vai receber acesso.' })
      return
    }

    setFieldErrors({})
    setIsSubmitting(true)
    try {
      const share = await sharingService.createTaskShare(taskId, email, permission)
      setShares((current) => [share, ...current])
      setEmail('')
      setPermission('read')
    } catch (err) {
      setFieldErrors(extractFieldErrors(err, 'Não foi possível compartilhar. Tente novamente.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleRemove(share: TaskShare) {
    const confirmed = window.confirm(`Remover o acesso de ${share.shared_with.email} a esta tarefa?`)
    if (!confirmed) return

    await sharingService.deleteTaskShare(taskId, share.id)
    setShares((current) => current.filter((item) => item.id !== share.id))
  }

  return (
    <div className="share-manager">
      <form onSubmit={handleSubmit} className="share-form" noValidate>
        <label>
          E-mail <span className="required-marker">*</span>
          <input
            type="email"
            value={email}
            placeholder="nome@exemplo.com"
            onChange={(event) => setEmail(event.target.value)}
          />
          {fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}
        </label>
        <label>
          Permissão
          <select
            value={permission}
            onChange={(event) => setPermission(event.target.value as SharePermission)}
          >
            <option value="read">Leitura</option>
            <option value="edit">Edição</option>
          </select>
        </label>
        <button type="submit" className={isSubmitting ? 'btn-loading' : undefined} disabled={isSubmitting}>
          Compartilhar
        </button>
      </form>
      <p className="field-hint">
        Leitura: a pessoa só pode visualizar a tarefa. Edição: a pessoa pode visualizar e editar a tarefa.
      </p>

      {fieldErrors.non_field_errors && <p className="error">{fieldErrors.non_field_errors}</p>}
      {loadError && (
        <div className="error error--with-action">
          <span>{loadError}</span>
          <button type="button" className="btn-secondary" onClick={loadShares}>
            Tentar novamente
          </button>
        </div>
      )}

      {isLoading ? (
        <p className="loading-state">Carregando compartilhamentos...</p>
      ) : shares.length === 0 ? (
        <p className="empty-state">Esta tarefa ainda não foi compartilhada.</p>
      ) : (
        <>
          <p className="field-hint">Pessoas com acesso a esta tarefa:</p>
          <ul className="share-list">
            {shares.map((share) => (
              <li key={share.id} className="share-item">
                <span>{share.shared_with.email}</span>
                <span>{share.permission === 'edit' ? 'Edição' : 'Leitura'}</span>
                <button type="button" onClick={() => handleRemove(share)}>
                  Remover
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
