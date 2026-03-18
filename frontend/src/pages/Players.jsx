import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Plus, Users } from 'lucide-react'
import { getPlayers } from '../api/players'
import { useAuth } from '../contexts/AuthContext'
import RiskBadge from '../components/RiskBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import AddPlayerModal from '../components/AddPlayerModal'

const POSITIONS = ['All', 'Defender', 'Forward', 'Goalkeeper', 'Midfielder']
const STATUSES  = ['All', 'active', 'injured', 'recovery']

export default function Players() {
  const { user } = useAuth()
  const [players, setPlayers] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [position, setPosition] = useState('All')
  const [status, setStatus] = useState('All')
  const [showAdd, setShowAdd] = useState(false)

  const fetchPlayers = () => {
    const params = { team_id: user?.team_id }
    if (position !== 'All') params.position = position
    if (status !== 'All') params.status = status
    setLoading(true)
    getPlayers(params)
      .then((r) => setPlayers(r.data))
      .finally(() => setLoading(false))
  }

  useEffect(fetchPlayers, [position, status, user])

  const filtered = players.filter((p) =>
    p.full_name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Players</h2>
          <p className="text-slate-500 text-sm">{players.length} players in roster</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Add Player
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9"
            placeholder="Search players…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select className="input w-auto" value={position} onChange={(e) => setPosition(e.target.value)}>
          {POSITIONS.map((p) => <option key={p}>{p}</option>)}
        </select>
        <select className="input w-auto" value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>

      {loading ? <LoadingSpinner /> : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr className="text-left text-slate-500">
                <th className="px-4 py-3">Player</th>
                <th className="px-4 py-3">Position</th>
                <th className="px-4 py-3">Age</th>
                <th className="px-4 py-3">BMI</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Injury Risk</th>
                <th className="px-4 py-3">Risk Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filtered.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3">
                    <Link to={`/players/${p.id}`} className="font-medium text-blue-600 hover:underline">
                      {p.full_name}
                    </Link>
                    <p className="text-xs text-slate-400">{p.nationality}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{p.position}</td>
                  <td className="px-4 py-3 text-slate-600">{p.age}</td>
                  <td className="px-4 py-3 text-slate-600">{p.bmi}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      p.status === 'active' ? 'bg-green-100 text-green-700'
                      : p.status === 'injured' ? 'bg-red-100 text-red-700'
                      : 'bg-amber-100 text-amber-700'
                    }`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="px-4 py-3"><RiskBadge level={p.latest_risk?.risk_level} /></td>
                  <td className="px-4 py-3 font-mono text-slate-700">
                    {p.latest_risk ? (p.latest_risk.injury_risk_score * 100).toFixed(1) + '%' : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div className="flex flex-col items-center py-16 text-slate-400">
              <Users size={40} className="mb-2 opacity-30" />
              <p>No players found</p>
            </div>
          )}
        </div>
      )}

      {showAdd && <AddPlayerModal teamId={user?.team_id} onClose={() => { setShowAdd(false); fetchPlayers() }} />}
    </div>
  )
}
