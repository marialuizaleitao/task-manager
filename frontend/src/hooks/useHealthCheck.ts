import { useEffect, useState } from 'react'
import { checkHealth } from '../services/health'

type ConnectionState = 'checking' | 'online' | 'offline'

export function useHealthCheck(): ConnectionState {
  const [state, setState] = useState<ConnectionState>('checking')

  useEffect(() => {
    let cancelled = false

    checkHealth()
      .then(() => {
        if (!cancelled) setState('online')
      })
      .catch(() => {
        if (!cancelled) setState('offline')
      })

    return () => {
      cancelled = true
    }
  }, [])

  return state
}
