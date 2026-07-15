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
      <h2>Google Calendar</h2>

      {feedback === 'connected' && <p className="status status--online">Conta conectada com sucesso.</p>}
      {feedback === 'error' && (
        <p className="error">Não foi possível conectar sua conta Google. Tente novamente.</p>
      )}
      {error && <p className="error">{error}</p>}

      {isLoading ? (
        <p className="status">Carregando...</p>
      ) : status?.connected ? (
        <div className="task-item-row">
          <span className="status status--online">Conectado</span>
          <label>
            <input
              type="checkbox"
              checked={status.enabled}
              onChange={(event) => handleToggle(event.target.checked)}
            />
            Sincronizar tarefas com due_date automaticamente
          </label>
          <button type="button" onClick={handleDisconnect}>
            Desconectar
          </button>
        </div>
      ) : (
        <div className="task-item-row">
          <span className="status status--offline">Não conectado</span>
          <button type="button" onClick={handleConnect}>
            Conectar Google Calendar
          </button>
        </div>
      )}
    </section>
  )
}
