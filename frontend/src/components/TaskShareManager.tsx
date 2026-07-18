import { useEffect, useState, type FormEvent } from 'react'
import * as sharingService from '../services/sharing'
import type { SharePermission, TaskShare } from '../services/sharing'

interface TaskShareManagerProps {
  taskId: number
}

export function TaskShareManager({ taskId }: TaskShareManagerProps) {
  const [shares, setShares] = useState<TaskShare[]>([])
  const [email, setEmail] = useState('')
  const [permission, setPermission] = useState<SharePermission>('read')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadShares() {
    setIsLoading(true)
    try {
      const data = await sharingService.listTaskShares(taskId)
      setShares(data)
    } catch {
      setError('Não foi possível carregar os compartilhamentos.')
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
    setError(null)

    try {
      const share = await sharingService.createTaskShare(taskId, email, permission)
      setShares((current) => [share, ...current])
      setEmail('')
      setPermission('read')
    } catch {
      setError('Não foi possível compartilhar. Verifique o e-mail informado.')
    }
  }

  async function handleRemove(share: TaskShare) {
    await sharingService.deleteTaskShare(taskId, share.id)
    setShares((current) => current.filter((item) => item.id !== share.id))
  }

  return (
    <div className="share-manager">
      <form onSubmit={handleSubmit} className="share-form">
        <label>
          E-mail
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
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
        <button type="submit">Compartilhar</button>
      </form>

      {error && <p className="error">{error}</p>}

      {isLoading ? (
        <p className="loading-state">Carregando compartilhamentos...</p>
      ) : shares.length === 0 ? (
        <p className="empty-state">Esta tarefa ainda não foi compartilhada.</p>
      ) : (
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
      )}
    </div>
  )
}
