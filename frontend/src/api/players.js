import api from './axios'
export const getPlayers = (params) => api.get('/players/', { params })
export const getPlayer = (id) => api.get(`/players/${id}`)
export const createPlayer = (data) => api.post('/players/', data)
export const updatePlayer = (id, data) => api.put(`/players/${id}`, data)
export const deletePlayer = (id) => api.delete(`/players/${id}`)
export const addMetrics = (id, data) => api.post(`/players/${id}/metrics`, data)
export const getMetrics = (id) => api.get(`/players/${id}/metrics`)
