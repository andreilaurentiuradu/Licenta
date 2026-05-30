import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          // Refresh via Keycloak token endpoint (proxied through Vite)
          const params = new URLSearchParams({
            grant_type:    'refresh_token',
            client_id:     'lawranalyzer-client',
            refresh_token: refresh,
          })
          const { data } = await axios.post(
            '/realms/lawranalyzer/protocol/openid-connect/token',
            params,
            { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
          )
          localStorage.setItem('access_token', data.access_token)
          if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return api(original)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(err)
  },
)

export default api
