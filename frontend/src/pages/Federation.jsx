import { useEffect, useState } from 'react'
import { Network, Play, CheckCircle, Clock, XCircle } from 'lucide-react'
import { startRound, getRounds, getStatus } from '../api/federation'
import LoadingSpinner from '../components/LoadingSpinner'
import toast from 'react-hot-toast'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { getFLHistory } from '../api/analytics'

const STATUS_ICON = {
  completed: <CheckCircle size={16} className="text-green-500" />,
  active:    <Clock size={16} className="text-blue-500 animate-spin" />,
  failed:    <XCircle size={16} className="text-red-500" />,
  pending:   <Clock size={16} className="text-slate-400" />,
}

export default function Federation() {
  const [status, setStatus] = useState(null)
  const [rounds, setRounds] = useState([])
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)

  const load = () => {
    setLoading(true)
    Promise.all([getStatus(), getRounds(), getFLHistory()])
      .then(([s, r, h]) => {
        setStatus(s.data)
        setRounds(r.data)
        setHistory(h.data)
      })
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const handleStartRound = async () => {
    setRunning(true)
    try {
      const r = await startRound()
      toast.success(`Round ${r.data.round.round_number} completed! Accuracy: ${(r.data.round.global_accuracy * 100).toFixed(2)}%`)
      load()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to start FL round')
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Federated Learning</h2>
          <p className="text-slate-500 text-sm">Privacy-preserving collaborative model training (FedAvg)</p>
        </div>
        <button onClick={handleStartRound} disabled={running} className="btn-primary flex items-center gap-2">
          <Play size={16} />
          {running ? 'Training…' : 'Start FL Round'}
        </button>
      </div>

      {/* Status cards */}
      {status && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="card text-center">
            <p className="text-sm text-slate-500">Total Rounds</p>
            <p className="text-3xl font-bold text-slate-800">{status.total_rounds}</p>
          </div>
          <div className="card text-center">
            <p className="text-sm text-slate-500">Model Version</p>
            <p className="text-3xl font-bold text-slate-800">v{status.current_model_version}</p>
          </div>
          <div className="card text-center">
            <p className="text-sm text-slate-500">Last Accuracy</p>
            <p className="text-3xl font-bold text-slate-800">
              {status.last_global_accuracy ? `${(status.last_global_accuracy * 100).toFixed(1)}%` : '—'}
            </p>
          </div>
          <div className="card text-center">
            <p className="text-sm text-slate-500">Participating Teams</p>
            <p className="text-3xl font-bold text-slate-800">{status.participating_teams}</p>
          </div>
        </div>
      )}

      {/* FL Principles banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
        <h3 className="font-semibold text-blue-800 flex items-center gap-2 mb-2">
          <Network size={18} /> Privacy-by-Design Architecture
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-blue-700">
          <div>
            <p className="font-medium">Local Training</p>
            <p className="text-blue-600 text-xs mt-1">Raw player data never leaves each club's infrastructure.</p>
          </div>
          <div>
            <p className="font-medium">Parameter Sharing Only</p>
            <p className="text-blue-600 text-xs mt-1">Only model weights (W₁, b₁, W₂, b₂) are transmitted — no biometric data.</p>
          </div>
          <div>
            <p className="font-medium">FedAvg Aggregation</p>
            <p className="text-blue-600 text-xs mt-1">θ_global = Σ (nₖ / n_total) × θₖ — weighted by local dataset size.</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Accuracy chart */}
        {history.length > 0 && (
          <div className="card">
            <h3 className="font-semibold text-slate-700 mb-3">Global Model Performance</h3>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="round" tick={{ fontSize: 11 }} label={{ value: 'Round', position: 'insideBottom', offset: -3 }} />
                <YAxis tick={{ fontSize: 11 }} domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                <Tooltip formatter={(v) => `${(v * 100).toFixed(2)}%`} />
                <Legend />
                <Line type="monotone" dataKey="accuracy" stroke="#2563eb" name="Accuracy" strokeWidth={2} dot />
                <Line type="monotone" dataKey="loss" stroke="#ef4444" name="Loss" strokeWidth={2} dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Participating teams */}
        {status?.teams && (
          <div className="card">
            <h3 className="font-semibold text-slate-700 mb-3">Participating Clubs</h3>
            <div className="space-y-3">
              {status.teams.map((t) => (
                <div key={t.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                  <div>
                    <p className="font-medium text-slate-800 text-sm">{t.name}</p>
                    <p className="text-xs text-slate-500">{t.data_points} local data points</p>
                  </div>
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Active</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Rounds table */}
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100 font-semibold text-slate-700 text-sm">
          Federation Rounds History
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-left">
              <tr>
                <th className="px-4 py-2">Round</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Teams</th>
                <th className="px-4 py-2">Data Points</th>
                <th className="px-4 py-2">Accuracy</th>
                <th className="px-4 py-2">Loss</th>
                <th className="px-4 py-2">Model</th>
                <th className="px-4 py-2">Completed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {rounds.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-mono">#{r.round_number}</td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-1.5">
                      {STATUS_ICON[r.status]}
                      <span className="capitalize text-xs">{r.status}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2">{r.participating_teams}</td>
                  <td className="px-4 py-2">{r.total_data_points}</td>
                  <td className="px-4 py-2 font-mono text-green-700">
                    {r.global_accuracy ? `${(r.global_accuracy * 100).toFixed(2)}%` : '—'}
                  </td>
                  <td className="px-4 py-2 font-mono text-red-600">
                    {r.global_loss ? r.global_loss.toFixed(4) : '—'}
                  </td>
                  <td className="px-4 py-2 text-slate-500">v{r.model_version}</td>
                  <td className="px-4 py-2 text-slate-500 text-xs">
                    {r.completed_at ? new Date(r.completed_at).toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rounds.length === 0 && (
            <p className="text-center py-10 text-slate-400 text-sm">No rounds yet. Click "Start FL Round" to begin.</p>
          )}
        </div>
      </div>
    </div>
  )
}
