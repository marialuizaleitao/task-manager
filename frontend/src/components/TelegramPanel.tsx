import { useEffect, useState } from 'react'
import * as telegramService from '../services/telegram'
import type { TelegramStatus } from '../services/telegram'

export function TelegramPanel() {
  const [status, setStatus] = useState<TelegramStatus | null>(null)
  const [deepLink, setDeepLink] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isChecking, setIsChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pendingMessage, setPendingMessage] = useState<string | null>(null)

  async function loadStatus() {
    setIsLoading(true)
    try {
      const data = await telegramService.getStatus()
      setStatus(data)
      if (data.connected) setDeepLink(null)
    } catch {
      setError('Não foi possível carregar o status da integração com o Telegram.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [])

  async function handleConnect() {
    setError(null)
    setPendingMessage(null)
    try {
      const data = await telegramService.startLinking()
      setDeepLink(data.deep_link)
      window.open(data.deep_link, '_blank', 'noopener,noreferrer')
    } catch {
      setError('Não foi possível iniciar a conexão com o Telegram.')
    }
  }

  async function handleConfirm() {
    setError(null)
    setIsChecking(true)
    try {
      const data = await telegramService.confirmLinking()
      if (data.connected) {
        setDeepLink(null)
        setPendingMessage(null)
        await loadStatus()
      } else {
        setPendingMessage(
          data.detail ?? 'Ainda não recebemos sua mensagem no Telegram. Abra o bot e envie /start.',
        )
      }
    } catch {
      setError('Não foi possível verificar a conexão com o Telegram.')
    } finally {
      setIsChecking(false)
    }
  }

  async function handleToggle(enabled: boolean) {
    setError(null)
    try {
      const updated = await telegramService.setNotificationsEnabled(enabled)
      setStatus(updated)
    } catch {
      setError('Não foi possível atualizar as notificações.')
    }
  }

  async function handleDisconnect() {
    const confirmed = window.confirm('Desconectar o Telegram? Você deixará de receber notificações de tarefas.')
    if (!confirmed) return

    setError(null)
    try {
      await telegramService.disconnect()
      setDeepLink(null)
      await loadStatus()
    } catch {
      setError('Não foi possível desconectar o Telegram.')
    }
  }

  return (
    <section className="telegram-panel">
      <div className="panel-header">
        <h2>Telegram</h2>
        {!isLoading && (
          <span className={`status status--${status?.connected ? 'online' : 'offline'}`}>
            {status?.connected
              ? `Conectado${status.telegram_username ? ` (@${status.telegram_username})` : ''}`
              : 'Não conectado'}
          </span>
        )}
      </div>

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
            Receber notificações de tarefas
          </label>
          <button type="button" className="btn-secondary" onClick={handleDisconnect}>
            Desconectar
          </button>
        </div>
      ) : (
        <div>
          <div className="task-item-row">
            <button type="button" onClick={handleConnect}>
              Conectar Telegram
            </button>
          </div>

          {deepLink && (
            <div className="task-item-row">
              <span>Abra o bot no Telegram e envie a mensagem inicial (/start) para concluir a vinculação.</span>
              <button type="button" onClick={handleConfirm} disabled={isChecking}>
                {isChecking ? 'Verificando...' : 'Verificar conexão'}
              </button>
            </div>
          )}

          {pendingMessage && <p className="status">{pendingMessage}</p>}
        </div>
      )}
    </section>
  )
}
