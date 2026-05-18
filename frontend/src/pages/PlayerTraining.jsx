import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts'
import { getTraining, addTraining, deleteTraining } from '../api/players'
import toast from 'react-hot-toast'

const inputCls = 'w-full bg-white/10 border border-white/20 rounded-xl px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:ring-2 focus:ring-white/30'
const labelCls = 'block text-xs font-medium text-white/60 mb-1'

const EMPTY = { date: '', training_hours: '', matches_played: '', notes: '' }

export default function PlayerTraining() {
  const { id }          = useParams()
  const [params]        = useSearchParams()
  const [logs,  setLogs]  = useState([])
  const [form,  setForm]  = useState(EMPTY)
  const [adding, setAdding] = useState(false)
  const [saving, setSaving] = useState(false)

  const load = () =>
    getTraining(id, { from: params.get('from') || undefined, to: params.get('to') || undefined })
      .then((r) => setLogs(r.data))
      .catch(() => toast.error('Failed to load training data'))

  useEffect(() => { load() }, [id, params.get('from'), params.get('to')])

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleAdd = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await addTraining(id, {
        date:           form.date,
        training_hours: form.training_hours ? parseFloat(form.training_hours) : null,
        matches_played: form.matches_played ? parseInt(form.matches_played)   : 0,
        notes:          form.notes || null,
      })
      setForm(EMPTY)
      setAdding(false)
      await load()
      toast.success('Entry added')
    } catch {
      toast.error('Failed to add entry')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (lid) => {
    try {
      await deleteTraining(id, lid)
      setLogs((l) => l.filter((e) => e.id !== lid))
      toast.success('Deleted')
    } catch {
      toast.error('Failed to delete')
    }
  }

  const chartData = logs.map((l) => ({
    date:           l.date,
    'Hours':        l.training_hours,
    'Matches':      l.matches_played,
  }))

  return (
    <div className="space-y-6">
      {/* Training hours chart */}
      {logs.length > 0 && (
        <div className="p-4 rounded-2xl bg-white/10 border border-white/15">
          <h2 className="text-sm font-semibold text-white mb-4">Training Hours</h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8 }} labelStyle={{ color: '#fff' }} />
              <Line type="monotone" dataKey="Hours" stroke="#60a5fa" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Matches chart */}
      {logs.length > 0 && (
        <div className="p-4 rounded-2xl bg-white/10 border border-white/15">
          <h2 className="text-sm font-semibold text-white mb-4">Matches Played</h2>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8 }} />
              <Bar dataKey="Matches" fill="#34d399" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Add form */}
      {!adding ? (
        <button
          onClick={() => setAdding(true)}
          className="px-4 py-2 rounded-xl bg-white/10 border border-white/20 text-xs text-white hover:bg-white/20 transition-all"
        >
          + Add entry
        </button>
      ) : (
        <form onSubmit={handleAdd} className="space-y-4 p-5 rounded-2xl bg-white/10 border border-white/15">
          <h2 className="text-sm font-semibold text-white">New Training Entry</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className={labelCls}>Date *</label>
              <input type="date" required className={inputCls} value={form.date} onChange={(e) => set('date', e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Training Hours</label>
              <input type="number" step="0.5" min="0" className={inputCls} placeholder="1.5" value={form.training_hours} onChange={(e) => set('training_hours', e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Matches Played</label>
              <input type="number" min="0" className={inputCls} placeholder="0" value={form.matches_played} onChange={(e) => set('matches_played', e.target.value)} />
            </div>
            <div className="col-span-2">
              <label className={labelCls}>Notes</label>
              <input type="text" className={inputCls} placeholder="Optional notes" value={form.notes} onChange={(e) => set('notes', e.target.value)} />
            </div>
          </div>
          <div className="flex gap-3">
            <button type="submit" disabled={saving} className="px-4 py-2 rounded-xl bg-white/20 text-white text-xs font-semibold hover:bg-white/30 transition-all disabled:opacity-50">
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button type="button" onClick={() => { setAdding(false); setForm(EMPTY) }} className="px-4 py-2 rounded-xl bg-white/5 text-white/50 text-xs hover:text-white transition-all">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Table */}
      {logs.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-white/15">
          <table className="w-full text-xs text-white/70">
            <thead>
              <tr className="border-b border-white/10 bg-white/5">
                <th className="text-left px-4 py-3 font-medium text-white/50">Date</th>
                <th className="text-left px-4 py-3 font-medium text-white/50">Hours</th>
                <th className="text-left px-4 py-3 font-medium text-white/50">Matches</th>
                <th className="text-left px-4 py-3 font-medium text-white/50">Notes</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                  <td className="px-4 py-3">{l.date}</td>
                  <td className="px-4 py-3">{l.training_hours ?? '—'}</td>
                  <td className="px-4 py-3">{l.matches_played ?? 0}</td>
                  <td className="px-4 py-3 text-white/40">{l.notes || '—'}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => handleDelete(l.id)} className="text-white/30 hover:text-red-400 transition-colors">✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {logs.length === 0 && !adding && (
        <p className="text-white/30 text-sm text-center py-8">No training entries yet.</p>
      )}
    </div>
  )
}
