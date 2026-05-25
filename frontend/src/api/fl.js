import api from './axios'

export const triggerFLRound = () => api.post('/fl/train')
