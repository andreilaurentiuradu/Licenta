import api from './axios'

export const triggerFLRound = () => api.post('/fl/train')
export const getFlStatus    = () => api.get('/fl/status')
