import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import {
  ResponsiveContainer, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts'
import { getPhysical, addPhysical, deletePhysical } from '../api/players'
import toast from 'react-hot-toast'

const inputCls = 'w-full bg-white/10 border border-white/20 rounded-xl px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:ring-2 focus:ring-white/30'
const labelCls = 'block text-xs font-medium text-white/60 mb-1'

const EMPTY = { date: '', knee_strength_score: '', hamstring_flexibility: '', reaction_time_ms: '' }

export default function PlayerPhysical() {
  const { id }          = useParams()
  const [params]        = useSearchParams()
  const [recs,  setRecs]  = useState([])
  const [form,  setForm]  = useState(EMPTY)
  const [adding, setAdding] = useState(false)
  const [saving, setSaving] = useState(false)

  const load = () =>
    getPhysical(id, { from: params.get('from') || undefined, to: params.get('to') || undefined })
      .then((r) => setRecs(r.data))
      .catch(() => toast.error('Failed to load physical data'))

  useEffect(() => { load() }, [id, params.get('from'), params.get('to')])

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleAdd = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await addPhysical(id, {
        date:                  form.date,
        knee_strength_score:   form.knee_strength_score   ? parseFloat(form.knee_strength_score)   : null,
        hamstring_flexibility: form.hamstring_flexibility ? parseFloat(form.hamstring_flexibility) : null,
        reaction_time_ms:      form.reaction_time_ms      ? parseFloat(form.reaction_time_ms)      : null,
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

  const handleDelete = async (aid) => {
    try {
      await deletePhysical(id, aid)
      setRecs((r) => r.filter((e) => e.id !== aid))
      toast.success('Deleted')
    } catch {
      toast.error('Failed to delete')
    }
  }

  const chartData = recs.map((r) => ({
    date:          r.date,
    'Knee Str.':   r.knee_strength_score,
    'Hamstring':   r.hamstring_flexibility,
    'Reaction ms': r.reaction_time_ms,
  }))

  return (
    <div className="space-y-6">
      {recs.length > 0 && (
        <div className="p-4 rounded-2xl bg-white/10 border border-white/15">
          <h2 className="text-sm font-semibold text-white mb-4">Physical Parameters Over Time</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }} />
              <Line type="monotone" dataKey="Knee Str."   stroke="#60a5fa" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="Hamstring"   stroke="#34d399" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="Reaction ms" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {!adding ? (
        <button onClick={() => setAdding(true)} className="px-4 py-2 rounded-xl bg-white/10 border border-white/20 text-xs text-white hover:bg-white/20 transition-all">
          + Add assessment
        </button>
      ) : (
        <form onSubmit={handleAdd} className="space-y-4 p-5 rounded-2xl bg-white/10 border border-white/15">
          <h2 className="text-sm font-semibold text-white">New Physical Assessment</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className={labelCls}>Date *</label>
              <input type="date" required className={inputCls} value={form.date} onChange={(e) => set('date', e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Knee Strength Score</label>
              <input type="number" step="0.1" className={inputCls} placeholder="85.0" value={form.knee_strength_score} onChange={(e) => set('knee_strength_score', e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Hamstring Flexibility</label>
              <input type="number" step="0.1" className={inputCls} placeholder="72.5" value={form.hamstring_flexibility} onChange={(e) => set('hamstring_flexibility', e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Reaction Time (ms)</label>
              <input type="number" step="1" className={inputCls} placeholder="250" value={form.reaction_time_ms} onChange={(e) => set('reaction_time_ms', e.target.value)} />
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

      {recs.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-white/15">
          <table className="w-full text-xs text-white/70">
            <thead>
              <tr className="border-b border-white/10 bg-white/5">
                <th className="text-left px-4 py-3 font-medium text-white/50">Date</th>
                <th className="text-left px-4 py-3 font-medium text-white/50">Knee Str.</th>
                <th className="text-left px-4 py-3 font-medium text-white/50">Hamstring</th>
                <th className="text-left px-4 py-3 font-medium text-white/50">Reaction ms</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {recs.map((r) => (
                <tr key={r.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                  <td className="px-4 py-3">{r.date}</td>
                  <td className="px-4 py-3">{r.knee_strength_score ?? '—'}</td>
                  <td className="px-4 py-3">{r.hamstring_flexibility ?? '—'}</td>
                  <td className="px-4 py-3">{r.reaction_time_ms ?? '—'}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => handleDelete(r.id)} className="text-white/30 hover:text-red-400 transition-colors">✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {recs.length === 0 && !adding && (
        <p className="text-white/30 text-sm text-center py-8">No physical assessments yet.</p>
      )}
    </div>
  )
}
