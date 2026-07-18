import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import * as googleCalendarService from '../services/googleCalendar'
import type { GoogleCalendarStatus } from '../services/googleCalendar'

export function GoogleCalendarPanel() {
  const [status, setStatus] = useState<GoogleCalendarStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()

  async function loadStatus() {
    setIsLoading(true)
    try {
      const data = await googleCalendarService.getStatus()
      setStatus(data)
    } catch {
      setError('Não foi possível carregar o status da integração com o Google Calendar.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()

    if (searchParams.get('google_calendar')) {
      setSearchParams(
        (params) => {
          params.delete('google_calendar')
          return params
        },
        { replace: true },
      )
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleConnect() {
    setError(null)
    try {
      const authorizationUrl = await googleCalendarService.getAuthorizationUrl()
      window.location.href = authorizationUrl
    } catch {
      setError('Não foi possível iniciar a conexão com o Google.')
    }
  }

  async function handleToggle(enabled: boolean) {
    setError(null)
    try {
      const updated = await googleCalendarService.setSyncEnabled(enabled)
      setStatus(updated)
    } catch {
      setError('Não foi possível atualizar a sincronização.')
    }
  }

  async function handleDisconnect() {
    const confirmed = window.confirm(
      'Desconectar o Google Calendar? Os eventos já criados na sua agenda não serão removidos automaticamente.',
    )
    if (!confirmed) return

    setError(null)
    try {
      await googleCalendarService.disconnect()
      await loadStatus()
    } catch {
      setError('Não foi possível desconectar o Google Calendar.')
    }
  }

  const feedback = searchParams.get('google_calendar')

  return (
    <section className="google-calendar-panel">
      <div className="panel-header">
        <h2>Google Calendar</h2>
        {!isLoading && (
          <span className={`status status--${status?.connected ? 'online' : 'offline'}`}>
            {status?.connected ? 'Conectado' : 'Não conectado'}
          </span>
        )}
      </div>

      {feedback === 'connected' && <p className="status status--online">Conta conectada com sucesso.</p>}
      {feedback === 'error' && (
        <p className="error">Não foi possível conectar sua conta Google. Tente novamente.</p>
      )}
      {error && <p className="error">{error}</p>}

      {isLoading ? (
        <p className="loading-state">Carregando...</p>
      ) : status?.connected ? (
        <div className="task-item-row">
          <label>
            <input
              type="checkbox"
              checked={status.enabled}
              onChange={(event) => handleToggle(event.target.checked)}
            />
            Sincronizar tarefas com data de vencimento
          </label>
          <button type="button" className="btn-secondary" onClick={handleDisconnect}>
            Desconectar
          </button>
        </div>
      ) : (
        <div>
          <p className="field-hint">
            Conecte para sincronizar automaticamente suas tarefas com data de vencimento na sua agenda do Google.
          </p>
          <div className="task-item-row">
            <button type="button" onClick={handleConnect}>
              Conectar agenda do Google
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
