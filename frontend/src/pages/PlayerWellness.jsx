import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts'
import { getWellness, addWellness, deleteWellness } from '../api/players'
import toast from 'react-hot-toast'

const inputCls = 'w-full bg-white/10 border border-white/20 rounded-xl px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:ring-2 focus:ring-white/30'
const labelCls = 'block text-xs font-medium text-white/60 mb-1'

const EMPTY = {
  date: '', calories: '', protein_g: '', carbs_g: '', fat_g: '', hydration_ml: '',
  sleep_hours: '', sleep_quality: '', stress_level: '', mood_score: '', notes: '',
}

export default function PlayerWellness() {
  const { id }          = useParams()
  const [params]        = useSearchParams()
  const [logs,  setLogs]  = useState([])
  const [form,  setForm]  = useState(EMPTY)
  const [adding, setAdding] = useState(false)
  const [saving, setSaving] = useState(false)

  const load = () =>
    getWellness(id, { from: params.get('from') || undefined, to: params.get('to') || undefined })
      .then((r) => setLogs(r.data))
      .catch(() => toast.error('Failed to load wellness data'))

  useEffect(() => { load() }, [id, params.get('from'), params.get('to')])

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleAdd = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const n = (v) => (v !== '' && v !== null && v !== undefined ? parseFloat(v) : null)
      await addWellness(id, {
        date:          form.date,
        calories:      n(form.calories),
        protein_g:     n(form.protein_g),
        carbs_g:       n(form.carbs_g),
        fat_g:         n(form.fat_g),
        hydration_ml:  n(form.hydration_ml),
        sleep_hours:   n(form.sleep_hours),
        sleep_quality: n(form.sleep_quality),
        stress_level:  n(form.stress_level),
        mood_score:    n(form.mood_score),
        notes:         form.notes || null,
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
      await deleteWellness(id, lid)
      setLogs((l) => l.filter((e) => e.id !== lid))
      toast.success('Deleted')
    } catch {
      toast.error('Failed to delete')
    }
  }

  const nutritionData = logs.map((l) => ({
    date:       l.date,
    'Protein':  l.protein_g,
    'Carbs':    l.carbs_g,
    'Fat':      l.fat_g,
    'Calories': l.calories,
  }))

  const sleepStressData = logs.map((l) => ({
    date:          l.date,
    'Sleep h':     l.sleep_hours,
    'Sleep Qual.': l.sleep_quality,
    'Stress':      l.stress_level,
    'Mood':        l.mood_score,
  }))

  return (
    <div className="space-y-6">
      {/* Nutrition chart */}
      {logs.length > 0 && (
        <div className="p-4 rounded-2xl bg-white/10 border border-white/15">
          <h2 className="text-sm font-semibold text-white mb-4">Nutrition (macros in g)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={nutritionData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }} />
              <Bar dataKey="Protein" stackId="a" fill="#60a5fa" />
              <Bar dataKey="Carbs"   stackId="a" fill="#34d399" />
              <Bar dataKey="Fat"     stackId="a" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Sleep / stress chart */}
      {logs.length > 0 && (
        <div className="p-4 rounded-2xl bg-white/10 border border-white/15">
          <h2 className="text-sm font-semibold text-white mb-4">Sleep &amp; Stress (scores 1–10)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={sleepStressData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} />
              <YAxis domain={[0, 10]} tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }} />
              <Line type="monotone" dataKey="Sleep h"     stroke="#60a5fa" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="Sleep Qual." stroke="#34d399" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="Stress"      stroke="#f87171" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="Mood"        stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {!adding ? (
        <button onClick={() => setAdding(true)} className="px-4 py-2 rounded-xl bg-white/10 border border-white/20 text-xs text-white hover:bg-white/20 transition-all">
          + Add entry
        </button>
      ) : (
        <form onSubmit={handleAdd} className="space-y-4 p-5 rounded-2xl bg-white/10 border border-white/15">
          <h2 className="text-sm font-semibold text-white">New Wellness Entry</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className={labelCls}>Date *</label>
              <input type="date" required className={inputCls} value={form.date} onChange={(e) => set('date', e.target.value)} />
            </div>
            {[
              { k: 'calories',      label: 'Calories (kcal)',    placeholder: '2200' },
              { k: 'protein_g',     label: 'Protein (g)',         placeholder: '150' },
              { k: 'carbs_g',       label: 'Carbs (g)',           placeholder: '280' },
              { k: 'fat_g',         label: 'Fat (g)',             placeholder: '70'  },
              { k: 'hydration_ml',  label: 'Hydration (ml)',      placeholder: '2500'},
              { k: 'sleep_hours',   label: 'Sleep Hours',         placeholder: '7.5' },
              { k: 'sleep_quality', label: 'Sleep Quality (1–10)',placeholder: '8'   },
              { k: 'stress_level',  label: 'Stress Level (1–10)', placeholder: '4'   },
              { k: 'mood_score',    label: 'Mood Score (1–10)',   placeholder: '7'   },
            ].map(({ k, label, placeholder }) => (
              <div key={k}>
                <label className={labelCls}>{label}</label>
                <input type="number" step="0.1" min="0" className={inputCls} placeholder={placeholder}
                  value={form[k]} onChange={(e) => set(k, e.target.value)} />
              </div>
            ))}
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

      {logs.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-white/15">
          <table className="w-full text-xs text-white/70">
            <thead>
              <tr className="border-b border-white/10 bg-white/5">
                {['Date', 'Cal', 'P(g)', 'C(g)', 'F(g)', 'H2O ml', 'Sleep h', 'Qual.', 'Stress', 'Mood', ''].map((h) => (
                  <th key={h} className="text-left px-3 py-3 font-medium text-white/50 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                  <td className="px-3 py-3 whitespace-nowrap">{l.date}</td>
                  <td className="px-3 py-3">{l.calories ?? '—'}</td>
                  <td className="px-3 py-3">{l.protein_g ?? '—'}</td>
                  <td className="px-3 py-3">{l.carbs_g ?? '—'}</td>
                  <td className="px-3 py-3">{l.fat_g ?? '—'}</td>
                  <td className="px-3 py-3">{l.hydration_ml ?? '—'}</td>
                  <td className="px-3 py-3">{l.sleep_hours ?? '—'}</td>
                  <td className="px-3 py-3">{l.sleep_quality ?? '—'}</td>
                  <td className="px-3 py-3">{l.stress_level ?? '—'}</td>
                  <td className="px-3 py-3">{l.mood_score ?? '—'}</td>
                  <td className="px-3 py-3 text-right">
                    <button onClick={() => handleDelete(l.id)} className="text-white/30 hover:text-red-400 transition-colors">✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {logs.length === 0 && !adding && (
        <p className="text-white/30 text-sm text-center py-8">No wellness entries yet.</p>
      )}
    </div>
  )
}
