import { api } from './api'

export interface GoogleCalendarStatus {
  connected: boolean
  enabled: boolean
  calendar_id?: string
  updated_at?: string
}

export async function getStatus(): Promise<GoogleCalendarStatus> {
  const { data } = await api.get<GoogleCalendarStatus>('/integrations/google-calendar/status/')
  return data
}

export async function getAuthorizationUrl(): Promise<string> {
  const { data } = await api.get<{ authorization_url: string }>('/integrations/google-calendar/connect/')
  return data.authorization_url
}

export async function setSyncEnabled(enabled: boolean): Promise<GoogleCalendarStatus> {
  const { data } = await api.post<GoogleCalendarStatus>('/integrations/google-calendar/toggle/', { enabled })
  return data
}

export async function disconnect(): Promise<void> {
  await api.delete('/integrations/google-calendar/disconnect/')
}
