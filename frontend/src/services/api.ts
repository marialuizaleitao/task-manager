import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { tokenStorage } from './tokenStorage'

const baseURL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

export const api = axios.create({ baseURL })

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const refresh = tokenStorage.getRefreshToken()
  if (!refresh) {
    throw new Error('Sem refresh token disponível.')
  }

  const { data } = await axios.post<{ access: string; refresh?: string }>(
    `${baseURL}/auth/login/refresh/`,
    { refresh },
  )
  tokenStorage.setTokens(data.access, data.refresh ?? refresh)
  return data.access
}

type RetriableRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean }

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetriableRequestConfig | undefined

    if (error.response?.status !== 401 || !originalRequest || originalRequest._retry) {
      throw error
    }

    originalRequest._retry = true

    try {
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null
      })
      const newAccessToken = await refreshPromise
      originalRequest.headers.set('Authorization', `Bearer ${newAccessToken}`)
      return api(originalRequest)
    } catch (refreshError) {
      tokenStorage.clear()
      throw refreshError
    }
  },
)

/**
 * Extrai mensagens de erro por campo de uma resposta de validação do DRF.
 *
 * O DRF retorna `{ campo: ["mensagem"] }` (ou `{ non_field_errors: [...] }`
 * para erros que não pertencem a um campo específico). Formulários usam o
 * retorno para exibir cada mensagem junto ao campo correspondente, em vez de
 * descartar o motivo real da falha.
 */
export function extractFieldErrors(error: unknown): Record<string, string> {
  if (!axios.isAxiosError(error) || !error.response?.data || typeof error.response.data !== 'object') {
    return {}
  }

  const data = error.response.data as Record<string, unknown>
  const fieldErrors: Record<string, string> = {}

  for (const [field, value] of Object.entries(data)) {
    if (Array.isArray(value) && typeof value[0] === 'string') {
      fieldErrors[field] = value[0]
    } else if (typeof value === 'string') {
      fieldErrors[field] = value
    }
  }

  return fieldErrors
}
