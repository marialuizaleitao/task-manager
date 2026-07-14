import { api } from './api'

export interface HealthStatus {
  status: string
}

export async function checkHealth(): Promise<HealthStatus> {
  const { data } = await api.get<HealthStatus>('/health/')
  return data
}
