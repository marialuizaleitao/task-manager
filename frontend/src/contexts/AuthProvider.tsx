import { useCallback, useEffect, useState, type ReactNode } from 'react'
import * as authService from '../services/auth'
import type { RegisterPayload, User } from '../services/auth'
import { tokenStorage } from '../services/tokenStorage'
import { AuthContext } from './AuthContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = tokenStorage.getAccessToken()
    if (!token) {
      setIsLoading(false)
      return
    }

    authService
      .fetchCurrentUser()
      .then(setUser)
      .catch(() => tokenStorage.clear())
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    await authService.login({ email, password })
    const currentUser = await authService.fetchCurrentUser()
    setUser(currentUser)
  }, [])

  const register = useCallback(
    async (payload: RegisterPayload) => {
      await authService.register(payload)
      await login(payload.email, payload.password)
    },
    [login],
  )

  const logout = useCallback(async () => {
    await authService.logout()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: user !== null, isLoading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}
