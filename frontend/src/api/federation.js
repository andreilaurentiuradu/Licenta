import api from './axios'
export const startRound = () => api.post('/federation/start')
export const getRounds = () => api.get('/federation/rounds')
export const getRound = (id) => api.get(`/federation/rounds/${id}`)
export const getStatus = () => api.get('/federation/status')
export const initFederation = () => api.post('/federation/init')
