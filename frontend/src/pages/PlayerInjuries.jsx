import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { getInjuries, addInjury, deleteInjury } from '../api/players'
import toast from 'react-hot-toast'

const inputCls = 'w-full bg-white/10 border border-white/20 rounded-xl px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:ring-2 focus:ring-white/30'
const labelCls = 'block text-xs font-medium text-white/60 mb-1'

const EMPTY = {
  date: '', injury_type: '', injury_severity: 'mild',
  rehabilitation_program: '', rehabilitation_weeks: '', recurrence: false, notes: '',
}

const SEVERITY_COLOR = {
  mild:     'bg-yellow-500/20 text-yellow-300',
  moderate: 'bg-orange-500/20 text-orange-300',
  severe:   'bg-red-500/20 text-red-300',
}

export default function PlayerInjuries() {
  const { id }          = useParams()
  const [params]        = useSearchParams()
  const [recs,  setRecs]  = useState([])
  const [form,  setForm]  = useState(EMPTY)
  const [adding, setAdding] = useState(false)
  const [saving, setSaving] = useState(false)

  const load = () =>
    getInjuries(id, { from: params.get('from') || undefined, to: params.get('to') || undefined })
      .then((r) => setRecs(r.data))
      .catch(() => toast.error('Failed to load injuries'))

  useEffect(() => { load() }, [id, params.get('from'), params.get('to')])

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleAdd = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await addInjury(id, {
        date:                   form.date,
        injury_type:            form.injury_type            || null,
        injury_severity:        form.injury_severity        || null,
        rehabilitation_program: form.rehabilitation_program || null,
        rehabilitation_weeks:   form.rehabilitation_weeks   ? parseInt(form.rehabilitation_weeks) : null,
        recurrence:             form.recurrence,
        notes:                  form.notes || null,
      })
      setForm(EMPTY)
      setAdding(false)
      await load()
      toast.success('Injury record added')
    } catch {
      toast.error('Failed to add entry')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (rid) => {
    try {
      await deleteInjury(id, rid)
      setRecs((r) => r.filter((e) => e.id !== rid))
      toast.success('Deleted')
    } catch {
      toast.error('Failed to delete')
    }
  }

  return (
    <div className="space-y-6">
      {!adding ? (
        <button onClick={() => setAdding(true)} className="px-4 py-2 rounded-xl bg-white/10 border border-white/20 text-xs text-white hover:bg-white/20 transition-all">
          + Add injury record
        </button>
      ) : (
        <form onSubmit={handleAdd} className="space-y-4 p-5 rounded-2xl bg-white/10 border border-white/15">
          <h2 className="text-sm font-semibold text-white">New Injury Record</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className={labelCls}>Date *</label>
              <input type="date" required className={inputCls} value={form.date} onChange={(e) => set('date', e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Injury Type</label>
              <input type="text" className={inputCls} placeholder="e.g. Hamstring strain" value={form.injury_type} onChange={(e) => set('injury_type', e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Severity</label>
              <select className={inputCls + ' bg-slate-900'} value={form.injury_severity} onChange={(e) => set('injury_severity', e.target.value)}>
                <option value="mild"     className="bg-slate-900">Mild</option>
                <option value="moderate" className="bg-slate-900">Moderate</option>
                <option value="severe"   className="bg-slate-900">Severe</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Rehab Program</label>
              <input type="text" className={inputCls} placeholder="e.g. RICE + physio" value={form.rehabilitation_program} onChange={(e) => set('rehabilitation_program', e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Rehab Weeks</label>
              <input type="number" min="0" className={inputCls} placeholder="3" value={form.rehabilitation_weeks} onChange={(e) => set('rehabilitation_weeks', e.target.value)} />
            </div>
            <div className="col-span-2 flex items-center gap-3">
              <input
                id="recurrence"
                type="checkbox"
                checked={form.recurrence}
                onChange={(e) => set('recurrence', e.target.checked)}
                className="w-4 h-4 rounded accent-white/50"
              />
              <label htmlFor="recurrence" className="text-xs text-white/60">Recurrence of a previous injury</label>
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

      {recs.length > 0 && (
        <div className="space-y-3">
          {recs.map((r) => (
            <div key={r.id} className="p-4 rounded-2xl bg-white/10 border border-white/15">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-xs text-white/40">{r.date}</span>
                    {r.injury_severity && (
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEVERITY_COLOR[r.injury_severity] || 'bg-white/10 text-white/50'}`}>
                        {r.injury_severity}
                      </span>
                    )}
                    {r.recurrence && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-medium">recurrence</span>
                    )}
                  </div>
                  <p className="text-sm font-semibold text-white">{r.injury_type || 'Unknown injury'}</p>
                  {r.rehabilitation_program && (
                    <p className="text-xs text-white/50 mt-1">
                      Rehab: {r.rehabilitation_program}
                      {r.rehabilitation_weeks ? ` · ${r.rehabilitation_weeks}w` : ''}
                    </p>
                  )}
                  {r.notes && <p className="text-xs text-white/30 mt-1">{r.notes}</p>}
                </div>
                <button onClick={() => handleDelete(r.id)} className="text-white/30 hover:text-red-400 transition-colors shrink-0">✕</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {recs.length === 0 && !adding && (
        <p className="text-white/30 text-sm text-center py-8">No injury records yet.</p>
      )}
    </div>
  )
}
