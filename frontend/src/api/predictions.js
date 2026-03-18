import api from './axios'
export const runPrediction = (playerId) => api.post(`/predictions/run/${playerId}`)
export const runTeamPredictions = (teamId) => api.post(`/predictions/run-team/${teamId}`)
export const getPredictions = (params) => api.get('/predictions/', { params })
