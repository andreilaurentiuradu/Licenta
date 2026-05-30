import { createContext, useContext, useState, useEffect } from 'react'
import { login as apiLogin, getMe } from '../api/auth'

const AuthContext = createContext(null)

/** Parse user info from a Keycloak JWT (no signature check — display only). */
function parseToken(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return {
      sub:      payload.sub,
      username: payload.preferred_username,
      email:    payload.email,
      roles:    payload.realm_access?.roles ?? [],
      club:     payload.club ?? null,
    }
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      getMe()
        .then((res) => setUser(res.data))
        .catch(() => localStorage.clear())
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (username, password) => {
    const { data } = await apiLogin(username, password)
    localStorage.setItem('access_token',  data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    try {
      const meRes = await getMe()
      const userData = meRes.data
      setUser(userData)
      // If club is missing (e.g. newly registered user, Keycloak attribute propagation delay),
      // retry once after 2s
      if (!userData.club) {
        setTimeout(async () => {
          try {
            const retry = await getMe()
            if (retry.data.club) setUser(retry.data)
          } catch { /* ignore */ }
        }, 2000)
      }
      return userData
    } catch {
      const parsed = parseToken(data.access_token)
      setUser(parsed)
      return parsed
    }
  }

  const logout = () => {
    localStorage.clear()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
