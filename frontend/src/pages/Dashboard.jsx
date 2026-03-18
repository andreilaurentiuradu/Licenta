import { useEffect, useState } from 'react'
import { Users, TrendingUp, AlertTriangle, Network, Activity } from 'lucide-react'
import { getOverview } from '../api/analytics'
import { getPlayers } from '../api/players'
import { useAuth } from '../contexts/AuthContext'
import StatCard from '../components/StatCard'
import RiskBadge from '../components/RiskBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const { user } = useAuth()
  const [overview, setOverview] = useState(null)
  const [highRiskPlayers, setHighRiskPlayers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const teamId = user?.team_id
    Promise.all([
      getOverview(teamId),
      getPlayers({ team_id: teamId }),
    ]).then(([ovRes, plRes]) => {
      setOverview(ovRes.data)
      // Filter players with high risk from latest_risk
      const hr = plRes.data
        .filter((p) => p.latest_risk?.risk_level === 'high')
        .slice(0, 6)
      setHighRiskPlayers(hr)
    }).finally(() => setLoading(false))
  }, [user])

  if (loading) return <LoadingSpinner />

  const o = overview

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Dashboard</h2>
        <p className="text-slate-500 text-sm mt-1">Welcome back, {user?.username}. Here's your team overview.</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Players" value={o?.players?.total} icon={Users} color="blue" />
        <StatCard label="Active" value={o?.players?.active} sub={`${o?.players?.injured} injured`} icon={Activity} color="green" />
        <StatCard label="High Risk" value={o?.predictions?.high_risk} sub="Injury alerts" icon={AlertTriangle} color="red" />
        <StatCard
          label="FL Model v{o?.federation?.model_version}"
          value={o?.federation?.latest_accuracy ? `${(o.federation.latest_accuracy * 100).toFixed(1)}%` : 'N/A'}
          sub={`${o?.federation?.completed_rounds} rounds`}
          icon={Network}
          color="purple"
        />
      </div>

      {/* Risk distribution row */}
      <div className="grid grid-cols-3 gap-4">
        {['low', 'medium', 'high'].map((level) => {
          const count = o?.predictions?.[`${level}_risk`] ?? 0
          const total = o?.predictions?.total || 1
          const pct = Math.round((count / total) * 100)
          return (
            <div key={level} className="card text-center">
              <p className="text-sm text-slate-500 capitalize mb-1">{level} Risk</p>
              <p className="text-3xl font-bold text-slate-800">{pct}%</p>
              <p className="text-xs text-slate-400">{count} players</p>
              <div className="mt-3 h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${level === 'high' ? 'bg-red-500' : level === 'medium' ? 'bg-amber-400' : 'bg-green-500'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* High-risk players table */}
      {highRiskPlayers.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <AlertTriangle size={18} className="text-red-500" />
            High Risk Players — Immediate Attention
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-slate-100">
                  <th className="pb-2 pr-4">Player</th>
                  <th className="pb-2 pr-4">Position</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Risk Score</th>
                  <th className="pb-2">Risk Level</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {highRiskPlayers.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50">
                    <td className="py-2 pr-4">
                      <Link to={`/players/${p.id}`} className="font-medium text-blue-600 hover:underline">
                        {p.full_name}
                      </Link>
                    </td>
                    <td className="py-2 pr-4 text-slate-600">{p.position}</td>
                    <td className="py-2 pr-4">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${p.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-slate-700">
                      {p.latest_risk ? (p.latest_risk.injury_risk_score * 100).toFixed(1) + '%' : '—'}
                    </td>
                    <td className="py-2">
                      <RiskBadge level={p.latest_risk?.risk_level} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Link to="/players" className="mt-3 inline-block text-sm text-blue-600 hover:underline">
            View all players →
          </Link>
        </div>
      )}
    </div>
  )
}
