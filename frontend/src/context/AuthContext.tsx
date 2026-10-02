import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useNavigate } from 'react-router-dom'

import { apiRequest, isUnauthorizedError } from '../services/apiClient'
import type { User } from '../types'

type AuthContextValue = {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  restoreAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()

  const restoreAuth = useCallback(async () => {
    setIsLoading(true)

    try {
      const response = await apiRequest<{ user: User }>('/api/v1/users/me', {
        method: 'GET',
      })
      setUser(response.user)
    } catch (error) {
      if (isUnauthorizedError(error)) {
        setUser(null)
      } else {
        setUser(null)
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const response = await apiRequest<{ user: User }>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    setUser(response.user)
    navigate('/dashboard')
  }, [navigate])

  const logout = useCallback(async () => {
    try {
      await apiRequest('/api/v1/auth/logout', { method: 'POST' })
    } catch {
      // Ignore logout failures and keep the UI consistent.
    } finally {
      setUser(null)
      navigate('/login')
    }
  }, [navigate])

  useEffect(() => {
    void restoreAuth()
  }, [restoreAuth])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      logout,
      restoreAuth,
    }),
    [isLoading, login, logout, restoreAuth, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }

  return context
}

export function AuthGuard({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <div>Checking your session...</div>
  }

  if (!isAuthenticated) {
    return <div>Redirecting...</div>
  }

  return <>{children}</>
}

export { AuthProvider }
