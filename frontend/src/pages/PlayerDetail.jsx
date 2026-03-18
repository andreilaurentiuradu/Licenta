import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Zap, Plus } from 'lucide-react'
import { getPlayer, addMetrics } from '../api/players'
import { runPrediction } from '../api/predictions'
import RiskBadge from '../components/RiskBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import toast from 'react-hot-toast'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'

const METRICS_FIELDS = [
  { key: 'training_hours_per_week',    label: 'Training Hours/Week',    step: '0.1', min: 0, max: 40 },
  { key: 'matches_played_past_season', label: 'Matches Past Season',     step: '1',   min: 0, max: 60 },
  { key: 'previous_injury_count',      label: 'Previous Injuries',       step: '1',   min: 0, max: 20 },
  { key: 'knee_strength_score',        label: 'Knee Strength (0-100)',   step: '0.1', min: 0, max: 100 },
  { key: 'hamstring_flexibility',      label: 'Hamstring Flexibility',   step: '0.1', min: 0, max: 100 },
  { key: 'reaction_time_ms',           label: 'Reaction Time (ms)',      step: '1',   min: 100, max: 500 },
  { key: 'balance_test_score',         label: 'Balance Score (0-100)',   step: '0.1', min: 0, max: 100 },
  { key: 'sprint_speed_10m_s',         label: 'Sprint Speed 10m (s)',    step: '0.01',min: 1, max: 10 },
  { key: 'agility_score',              label: 'Agility Score (0-100)',   step: '0.1', min: 0, max: 100 },
  { key: 'sleep_hours_per_night',      label: 'Sleep Hours/Night',       step: '0.1', min: 0, max: 12 },
  { key: 'stress_level_score',         label: 'Stress Level (0-100)',    step: '0.1', min: 0, max: 100 },
  { key: 'nutrition_quality_score',    label: 'Nutrition Quality (0-100)',step: '0.1',min: 0, max: 100 },
  { key: 'warmup_routine_adherence',   label: 'Warmup Adherence (0-1)',  step: '0.1', min: 0, max: 1 },
]

const defaultMetrics = Object.fromEntries(METRICS_FIELDS.map(f => [f.key, '']))

export default function PlayerDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [player, setPlayer] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [metrics, setMetrics] = useState(defaultMetrics)
  const [saving, setSaving] = useState(false)
  const [predicting, setPredicting] = useState(false)

  const load = () => {
    setLoading(true)
    getPlayer(id).then((r) => setPlayer(r.data)).finally(() => setLoading(false))
  }
  useEffect(load, [id])

  const handleAddMetrics = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = Object.fromEntries(
        Object.entries(metrics).map(([k, v]) => [k, Number(v)])
      )
      await addMetrics(id, payload)
      toast.success('Metrics recorded!')
      setShowForm(false)
      setMetrics(defaultMetrics)
      load()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error saving metrics')
    } finally {
      setSaving(false)
    }
  }

  const handlePredict = async () => {
    setPredicting(true)
    try {
      await runPrediction(id)
      toast.success('Prediction computed!')
      load()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Prediction failed')
    } finally {
      setPredicting(false)
    }
  }

  if (loading) return <LoadingSpinner />
  if (!player) return <p className="text-slate-500">Player not found</p>

  // Radar chart data from latest metrics
  const latest = player.metrics_history?.[0]
  const radarData = latest ? [
    { subject: 'Knee', value: latest.knee_strength_score },
    { subject: 'Flexibility', value: latest.hamstring_flexibility },
    { subject: 'Balance', value: latest.balance_test_score },
    { subject: 'Agility', value: latest.agility_score },
    { subject: 'Nutrition', value: latest.nutrition_quality_score },
    { subject: 'Sleep', value: latest.sleep_hours_per_night * 10 },
  ] : []

  // Risk trend chart
  const riskTrend = (player.metrics_history || [])
    .slice(0, 10)
    .reverse()
    .map((m, i) => ({ idx: i + 1, stress: m.stress_level_score, training: m.training_hours_per_week * 5 }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button onClick={() => navigate('/players')} className="mt-1 text-slate-400 hover:text-slate-600">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <h2 className="text-2xl font-bold text-slate-800">{player.full_name}</h2>
          <div className="flex flex-wrap gap-2 mt-1 text-sm text-slate-500">
            <span>{player.position}</span>·<span>Age {player.age}</span>·
            <span>{player.height_cm} cm / {player.weight_kg} kg</span>·
            <span>BMI {player.bmi}</span>·<span>{player.team_name}</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <RiskBadge level={player.latest_risk?.risk_level} />
          <span className="text-sm text-slate-500">
            {player.latest_risk ? (player.latest_risk.injury_risk_score * 100).toFixed(1) + '% risk' : ''}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: radar + actions */}
        <div className="space-y-4">
          {radarData.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-slate-700 mb-3">Performance Profile</h3>
              <ResponsiveContainer width="100%" height={220}>
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
                  <Radar dataKey="value" stroke="#2563eb" fill="#2563eb" fillOpacity={0.2} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="card space-y-2">
            <h3 className="font-semibold text-slate-700 mb-2">Actions</h3>
            <button
              onClick={() => setShowForm(!showForm)}
              className="btn-secondary w-full flex items-center justify-center gap-2"
            >
              <Plus size={16} /> Record Metrics
            </button>
            <button
              onClick={handlePredict}
              disabled={predicting || !player.metrics_history?.length}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              <Zap size={16} />
              {predicting ? 'Computing…' : 'Run Prediction'}
            </button>
            {!player.metrics_history?.length && (
              <p className="text-xs text-amber-600">Add metrics first to run prediction.</p>
            )}
          </div>
        </div>

        {/* Right: trend + metrics history */}
        <div className="lg:col-span-2 space-y-4">
          {riskTrend.length > 1 && (
            <div className="card">
              <h3 className="font-semibold text-slate-700 mb-3">Workload Trend</h3>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={riskTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="idx" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="stress" stroke="#ef4444" name="Stress" dot={false} />
                  <Line type="monotone" dataKey="training" stroke="#2563eb" name="Training×5" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="card overflow-x-auto p-0">
            <div className="px-4 py-3 border-b border-slate-100 font-semibold text-slate-700 text-sm">
              Metrics History
            </div>
            {player.metrics_history?.length ? (
              <table className="w-full text-xs">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-3 py-2 text-left">Date</th>
                    <th className="px-3 py-2">Training h</th>
                    <th className="px-3 py-2">Stress</th>
                    <th className="px-3 py-2">Sleep</th>
                    <th className="px-3 py-2">Knee</th>
                    <th className="px-3 py-2">Agility</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {player.metrics_history.map((m) => (
                    <tr key={m.id} className="hover:bg-slate-50">
                      <td className="px-3 py-2 text-slate-500">{new Date(m.recorded_at).toLocaleDateString()}</td>
                      <td className="px-3 py-2 text-center">{m.training_hours_per_week?.toFixed(1)}</td>
                      <td className="px-3 py-2 text-center">{m.stress_level_score?.toFixed(1)}</td>
                      <td className="px-3 py-2 text-center">{m.sleep_hours_per_night?.toFixed(1)}</td>
                      <td className="px-3 py-2 text-center">{m.knee_strength_score?.toFixed(1)}</td>
                      <td className="px-3 py-2 text-center">{m.agility_score?.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-center py-8 text-slate-400 text-sm">No metrics recorded yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Add metrics form */}
      {showForm && (
        <div className="card">
          <h3 className="font-semibold text-slate-700 mb-4">Record New Metrics</h3>
          <form onSubmit={handleAddMetrics}>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {METRICS_FIELDS.map(({ key, label, step, min, max }) => (
                <div key={key}>
                  <label className="label text-xs">{label}</label>
                  <input
                    type="number"
                    step={step}
                    min={min}
                    max={max}
                    className="input text-sm"
                    value={metrics[key]}
                    onChange={(e) => setMetrics((m) => ({ ...m, [key]: e.target.value }))}
                    required
                  />
                </div>
              ))}
            </div>
            <div className="flex gap-3 mt-4">
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
              <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save Metrics'}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
