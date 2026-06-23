import api from './axios'

// club is optional: admins may target a specific club, coaches train their own.
export const triggerFLRound  = (club) => api.post('/fl/train', club ? { club } : {})
export const getFlStatus     = () => api.get('/fl/status')
export const getFlClubs      = () => api.get('/fl/clubs')
export const getRiskRanking  = () => api.get('/fl/risk')
