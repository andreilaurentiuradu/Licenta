import { useEffect, useState } from 'react'
import { getOverview, getRiskDistribution, getFLHistory, getTeamComparison, getTeams } from '../api/analytics'
import LoadingSpinner from '../components/LoadingSpinner'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'

export default function Analytics() {
  const [teams, setTeams] = useState([])
  const [selectedTeam, setSelectedTeam] = useState('')
  const [overview, setOverview] = useState(null)
  const [riskDist, setRiskDist] = useState({})
  const [flHistory, setFlHistory] = useState([])
  const [teamComp, setTeamComp] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getTeams().then((r) => setTeams(r.data))
    getFLHistory().then((r) => setFlHistory(r.data))
    getTeamComparison().then((r) => setTeamComp(r.data))
  }, [])

  useEffect(() => {
    setLoading(true)
    const tid = selectedTeam ? +selectedTeam : null
    Promise.all([getOverview(tid), getRiskDistribution(tid)])
      .then(([o, r]) => { setOverview(o.data); setRiskDist(r.data) })
      .finally(() => setLoading(false))
  }, [selectedTeam])

  // Build position risk chart data
  const positionData = Object.entries(riskDist).map(([pos, counts]) => ({
    position: pos,
    Low: counts.low || 0,
    Medium: counts.medium || 0,
    High: counts.high || 0,
  }))

  // Pie data for status
  const statusData = overview ? [
    { name: 'Active', value: overview.players.active },
    { name: 'Injured', value: overview.players.injured },
    { name: 'Recovery', value: overview.players.recovery },
  ] : []
  const STATUS_COLORS = ['#22c55e', '#ef4444', '#f59e0b']

  if (loading && !overview) return <LoadingSpinner />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Analytics</h2>
          <p className="text-slate-500 text-sm">Insights across teams and FL performance</p>
        </div>
        <select
          className="input w-48"
          value={selectedTeam}
          onChange={(e) => setSelectedTeam(e.target.value)}
        >
          <option value="">All Teams</option>
          {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      </div>

      {/* Overview stats */}
      {overview && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-center">
          {[
            { label: 'Total Players', value: overview.players.total },
            { label: 'Total Predictions', value: overview.predictions.total },
            { label: 'High Risk', value: overview.predictions.high_risk, cls: 'text-red-600' },
            { label: 'FL Rounds', value: overview.federation.completed_rounds },
          ].map(({ label, value, cls }) => (
            <div key={label} className="card">
              <p className="text-sm text-slate-500">{label}</p>
              <p className={`text-3xl font-bold mt-1 ${cls || 'text-slate-800'}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Position × Risk */}
        {positionData.length > 0 && (
          <div className="card">
            <h3 className="font-semibold text-slate-700 mb-4">Risk by Position</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={positionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="position" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="High" fill="#ef4444" />
                <Bar dataKey="Medium" fill="#f59e0b" />
                <Bar dataKey="Low" fill="#22c55e" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Player status pie */}
        {overview && (
          <div className="card">
            <h3 className="font-semibold text-slate-700 mb-4">Player Status Distribution</h3>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={statusData} cx="50%" cy="50%" outerRadius={90} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {statusData.map((_, i) => <Cell key={i} fill={STATUS_COLORS[i]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* FL accuracy history */}
        {flHistory.length > 0 && (
          <div className="card">
            <h3 className="font-semibold text-slate-700 mb-4">Federated Model Accuracy over Rounds</h3>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={flHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="round" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} domain={[0, 1]} />
                <Tooltip formatter={(v) => `${(v * 100).toFixed(2)}%`} />
                <Line type="monotone" dataKey="accuracy" stroke="#2563eb" strokeWidth={2} dot name="Global Accuracy" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Team comparison */}
        {teamComp.length > 0 && (
          <div className="card">
            <h3 className="font-semibold text-slate-700 mb-4">Risk Comparison by Club</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={teamComp} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="team" type="category" tick={{ fontSize: 10 }} width={120} />
                <Tooltip />
                <Legend />
                <Bar dataKey="high" fill="#ef4444" name="High" />
                <Bar dataKey="medium" fill="#f59e0b" name="Medium" />
                <Bar dataKey="low" fill="#22c55e" name="Low" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}
