import axios from 'axios'
import api   from './axios'

const KC_TOKEN_URL = '/realms/sport-analytics/protocol/openid-connect/token'

/** Login via Keycloak direct grant (proxied through Vite → localhost:8080). */
export const login = (username, password) =>
  axios.post(
    KC_TOKEN_URL,
    new URLSearchParams({
      grant_type: 'password',
      client_id:  'sport-analytics-client',
      username,
      password,
    }),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
  )

/** Public registration — only coach/player roles. */
export const register = (data) => api.post('/auth/register', data)

/** Admin-only — create users with any role. */
export const adminCreateUser = (data) => api.post('/auth/admin/create-user', data)

/** Get current user info from Flask (validates token server-side). */
export const getMe = () => api.get('/auth/me')

/** Submit feedback (ratings + optional message). */
export const submitFeedback = (ratings, message) =>
  api.post('/feedback/', { ratings, message })
