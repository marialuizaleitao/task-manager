import { api } from './api'
import { tokenStorage } from './tokenStorage'

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  date_joined: string
}

export interface RegisterPayload {
  email: string
  password: string
  password_confirm: string
  first_name?: string
  last_name?: string
}

export interface LoginPayload {
  email: string
  password: string
}

export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await api.post<User>('/auth/register/', payload)
  return data
}

export async function login(payload: LoginPayload): Promise<void> {
  const { data } = await api.post<{ access: string; refresh: string }>('/auth/login/', payload)
  tokenStorage.setTokens(data.access, data.refresh)
}

export async function logout(): Promise<void> {
  const refresh = tokenStorage.getRefreshToken()
  try {
    if (refresh) {
      await api.post('/auth/logout/', { refresh })
    }
  } finally {
    tokenStorage.clear()
  }
}

export async function fetchCurrentUser(): Promise<User> {
  const { data } = await api.get<User>('/auth/me/')
  return data
}
