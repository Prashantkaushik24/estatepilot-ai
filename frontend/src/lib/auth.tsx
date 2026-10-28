import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, getToken, setToken, setUnauthorizedHandler } from './api'
import type { Role, User } from '../types'

interface AuthCtx { user: User | null; loading: boolean; login: (email: string, password: string) => Promise<void>; logout: () => void; can: (min: Role) => boolean }
const Ctx = createContext<AuthCtx>(null as any)
const rank: Record<Role, number> = { analyst: 0, agent: 1, manager: 2, admin: 3 }

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(!!getToken())
  const qc = useQueryClient()
  const logout = useCallback(() => { setToken(null); setUser(null); qc.clear() }, [qc])
  useEffect(() => { setUnauthorizedHandler(() => { logout() }) }, [logout])
  useEffect(() => {
    if (!getToken()) return
    api.get<User>('/auth/me').then(setUser).catch(() => setToken(null)).finally(() => setLoading(false))
  }, [])
  const login = async (email: string, password: string) => {
    const r = await api.post<{ access_token: string; user: User }>('/auth/login', { email, password })
    setToken(r.access_token); setUser(r.user)
  }
  /** can('agent') => role is agent or higher. analyst is read-only. */
  const can = (min: Role) => !!user && rank[user.role] >= rank[min]
  return <Ctx.Provider value={{ user, loading, login, logout, can }}>{children}</Ctx.Provider>
}
export const useAuth = () => useContext(Ctx)
