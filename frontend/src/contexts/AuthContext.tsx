import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { User } from '../types'

interface AuthState {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  register: (data: { email: string; full_name: string; password: string; organization_id?: string; role?: 'student' | 'faculty'; faculty_code?: string }) => Promise<User>
  logout: () => void
  refresh: () => Promise<void>
}

const Ctx = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(!!localStorage.getItem('token'))

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setUser(null)
  }, [])

  const refresh = useCallback(async () => {
    const { data } = await api.get<User>('/auth/me')
    setUser(data)
  }, [])

  useEffect(() => {
    if (localStorage.getItem('token')) refresh().catch(logout).finally(() => setLoading(false))
    const onLogout = () => logout()
    window.addEventListener('auth:logout', onLogout)
    return () => window.removeEventListener('auth:logout', onLogout)
  }, [refresh, logout])

  const accept = (data: { access_token: string; user: User }) => {
    localStorage.setItem('token', data.access_token)
    setUser(data.user)
    return data.user
  }

  const login = async (email: string, password: string) => accept((await api.post('/auth/login', { email, password })).data)
  const register: AuthState['register'] = async (body) => accept((await api.post('/auth/register', body)).data)

  return <Ctx.Provider value={{ user, loading, login, register, logout, refresh }}>{children}</Ctx.Provider>
}

export function useAuth() {
  const c = useContext(Ctx)
  if (!c) throw new Error('useAuth must be used inside AuthProvider')
  return c
}
