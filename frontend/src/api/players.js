import api from './axios'

export const getPlayers        = ()           => api.get('/players/')
export const getBiometrics     = (id)         => api.get(`/players/${id}/biometrics`)
export const upsertBiometrics  = (id, data)   => api.put(`/players/${id}/biometrics`, data)

export const getTraining       = (id, params) => api.get(`/players/${id}/training`,  { params })
export const addTraining       = (id, data)   => api.post(`/players/${id}/training`, data)
export const deleteTraining    = (id, lid)    => api.delete(`/players/${id}/training/${lid}`)

export const getPhysical       = (id, params) => api.get(`/players/${id}/physical`,  { params })
export const addPhysical       = (id, data)   => api.post(`/players/${id}/physical`, data)
export const deletePhysical    = (id, aid)    => api.delete(`/players/${id}/physical/${aid}`)

export const getInjuries       = (id, params) => api.get(`/players/${id}/injuries`,  { params })
export const addInjury         = (id, data)   => api.post(`/players/${id}/injuries`, data)
export const deleteInjury      = (id, rid)    => api.delete(`/players/${id}/injuries/${rid}`)

export const getWellness       = (id, params) => api.get(`/players/${id}/wellness`,  { params })
export const addWellness       = (id, data)   => api.post(`/players/${id}/wellness`, data)
export const deleteWellness    = (id, lid)    => api.delete(`/players/${id}/wellness/${lid}`)
