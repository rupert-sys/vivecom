import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { decodeToken, login as loginRequest, type JwtPayload } from '../api/auth'
import { getToken, setToken as persistToken } from '../api/client'

interface AuthContextValue {
  user: JwtPayload | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<JwtPayload | null>(() => {
    const token = getToken()
    return token ? decodeToken(token) : null
  })

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      login: async (email, password) => {
        const token = await loginRequest(email, password)
        persistToken(token)
        setUser(decodeToken(token))
      },
      logout: () => {
        persistToken(null)
        setUser(null)
      },
    }),
    [user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return context
}
