import { api } from './api'

export interface TelegramStatus {
  connected: boolean
  enabled: boolean
  telegram_username?: string
  last_contact_at?: string
}

export interface TelegramConnectResponse {
  deep_link: string
  bot_username: string
}

export async function getStatus(): Promise<TelegramStatus> {
  const { data } = await api.get<TelegramStatus>('/integrations/telegram/status/')
  return data
}

export async function startLinking(): Promise<TelegramConnectResponse> {
  const { data } = await api.get<TelegramConnectResponse>('/integrations/telegram/connect/')
  return data
}

export async function confirmLinking(): Promise<TelegramStatus & { detail?: string }> {
  const { data } = await api.post<TelegramStatus & { detail?: string }>('/integrations/telegram/confirm/')
  return data
}

export async function setNotificationsEnabled(enabled: boolean): Promise<TelegramStatus> {
  const { data } = await api.post<TelegramStatus>('/integrations/telegram/toggle/', { enabled })
  return data
}

export async function disconnect(): Promise<void> {
  await api.delete('/integrations/telegram/disconnect/')
}
