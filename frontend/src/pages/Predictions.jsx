import { useEffect, useState } from 'react'
import { TrendingUp, RefreshCw } from 'lucide-react'
import { getPredictions } from '../api/predictions'
import { runTeamPredictions } from '../api/predictions'
import { useAuth } from '../contexts/AuthContext'
import RiskBadge from '../components/RiskBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import toast from 'react-hot-toast'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const COLORS = { low: '#22c55e', medium: '#f59e0b', high: '#ef4444' }

export default function Predictions() {
  const { user } = useAuth()
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [riskFilter, setRiskFilter] = useState('all')

  const load = () => {
    setLoading(true)
    getPredictions({ team_id: user?.team_id, limit: 100 })
      .then((r) => setPredictions(r.data))
      .finally(() => setLoading(false))
  }
  useEffect(load, [user])

  const runAll = async () => {
    setRunning(true)
    try {
      const r = await runTeamPredictions(user.team_id)
      toast.success(`Predictions complete: ${r.data.processed} players processed`)
      load()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to run predictions')
    } finally {
      setRunning(false)
    }
  }

  const filtered = riskFilter === 'all' ? predictions : predictions.filter((p) => p.risk_level === riskFilter)

  const pieCounts = ['low', 'medium', 'high'].map((l) => ({
    name: l.charAt(0).toUpperCase() + l.slice(1),
    value: predictions.filter((p) => p.risk_level === l).length,
  }))

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Injury Risk Predictions</h2>
          <p className="text-slate-500 text-sm">{predictions.length} predictions recorded</p>
        </div>
        <button onClick={runAll} disabled={running} className="btn-primary flex items-center gap-2">
          <RefreshCw size={16} className={running ? 'animate-spin' : ''} />
          {running ? 'Running…' : 'Run All Predictions'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pie chart */}
        <div className="card">
          <h3 className="font-semibold text-slate-700 mb-3">Risk Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieCounts} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value">
                {pieCounts.map((entry) => (
                  <Cell key={entry.name} fill={COLORS[entry.name.toLowerCase()]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Table */}
        <div className="lg:col-span-2 card p-0 overflow-hidden">
          {/* Filter tabs */}
          <div className="flex border-b border-slate-100 px-4">
            {['all', 'high', 'medium', 'low'].map((f) => (
              <button
                key={f}
                onClick={() => setRiskFilter(f)}
                className={`px-3 py-3 text-sm font-medium border-b-2 transition-colors capitalize ${
                  riskFilter === f ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
                {f !== 'all' && <span className="ml-1 text-xs bg-slate-100 px-1.5 py-0.5 rounded-full">
                  {predictions.filter((p) => p.risk_level === f).length}
                </span>}
              </button>
            ))}
          </div>

          {loading ? <LoadingSpinner /> : (
            <div className="overflow-y-auto max-h-96">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 sticky top-0">
                  <tr className="text-slate-500 text-left">
                    <th className="px-4 py-2">Player ID</th>
                    <th className="px-4 py-2">Risk Score</th>
                    <th className="px-4 py-2">Level</th>
                    <th className="px-4 py-2">Model v</th>
                    <th className="px-4 py-2">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {filtered.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50">
                      <td className="px-4 py-2 font-mono text-slate-600">#{p.player_id}</td>
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden w-20">
                            <div
                              className={`h-full rounded-full ${p.risk_level === 'high' ? 'bg-red-500' : p.risk_level === 'medium' ? 'bg-amber-400' : 'bg-green-500'}`}
                              style={{ width: `${(p.injury_risk_score * 100).toFixed(0)}%` }}
                            />
                          </div>
                          <span className="font-mono text-xs">{(p.injury_risk_score * 100).toFixed(1)}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-2"><RiskBadge level={p.risk_level} /></td>
                      <td className="px-4 py-2 text-slate-500 text-xs">v{p.model_version}</td>
                      <td className="px-4 py-2 text-slate-500 text-xs">
                        {new Date(p.predicted_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
