import api from './axios'
export const getOverview = (teamId) => api.get('/analytics/overview', { params: teamId ? { team_id: teamId } : {} })
export const getRiskDistribution = (teamId) => api.get('/analytics/risk-distribution', { params: teamId ? { team_id: teamId } : {} })
export const getFLHistory = () => api.get('/analytics/fl-history')
export const getTeamComparison = () => api.get('/analytics/team-comparison')
export const getTeams = () => api.get('/teams/')
