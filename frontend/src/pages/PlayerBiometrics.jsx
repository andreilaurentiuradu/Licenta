import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { getBiometrics, upsertBiometrics } from '../api/players'
import toast from 'react-hot-toast'

const inputCls = 'w-full bg-white/10 border border-white/20 rounded-xl px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:ring-2 focus:ring-white/30'
const labelCls = 'block text-xs font-medium text-white/60 mb-1'

export default function PlayerBiometrics() {
  const { id }    = useParams()
  const { user }  = useAuth()
  const isPlayer  = user?.roles?.includes('player') && !user?.roles?.includes('coach') && !user?.roles?.includes('admin')

  const [data,    setData]    = useState(null)
  const [editing, setEditing] = useState(false)
  const [form,    setForm]    = useState({})
  const [saving,  setSaving]  = useState(false)

  useEffect(() => {
    getBiometrics(id)
      .then((r) => {
        setData(r.data)
        setForm(r.data)
      })
      .catch(() => toast.error('Failed to load biometrics'))
  }, [id])

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = {
        username:   form.username || user?.username || id,
        position:   form.position   || null,
        height_cm:  form.height_cm  ? parseFloat(form.height_cm)  : null,
        weight_kg:  form.weight_kg  ? parseFloat(form.weight_kg)  : null,
        birth_year: form.birth_year ? parseInt(form.birth_year)   : null,
      }
      const res = await upsertBiometrics(id, payload)
      setData(res.data)
      setForm(res.data)
      setEditing(false)
      toast.success('Biometrics saved')
    } catch {
      toast.error('Failed to save')
    } finally {
      setSaving(false)
    }
  }

  if (data === null) return <p className="text-white/40 text-sm">Loading…</p>

  const fields = [
    { key: 'position',   label: 'Position',         type: 'text',   placeholder: 'e.g. Midfielder' },
    { key: 'height_cm',  label: 'Height (cm)',       type: 'number', placeholder: '175' },
    { key: 'weight_kg',  label: 'Weight (kg)',       type: 'number', placeholder: '70' },
    { key: 'birth_year', label: 'Birth Year',        type: 'number', placeholder: '2000' },
  ]

  return (
    <div className="space-y-6">
      {/* Info cards */}
      {!editing && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: 'Position',   value: data.position   || '—' },
              { label: 'Height',     value: data.height_cm  ? `${data.height_cm} cm`  : '—' },
              { label: 'Weight',     value: data.weight_kg  ? `${data.weight_kg} kg`  : '—' },
              { label: 'Birth Year', value: data.birth_year || '—' },
            ].map((c) => (
              <div key={c.label} className="p-4 rounded-2xl bg-white/10 border border-white/15">
                <p className="text-xs text-white/40 mb-1">{c.label}</p>
                <p className="text-lg font-bold text-white">{c.value}</p>
              </div>
            ))}
          </div>
          <button
            onClick={() => setEditing(true)}
            className="px-4 py-2 rounded-xl bg-white/10 border border-white/20 text-xs text-white hover:bg-white/20 transition-all"
          >
            Edit biometrics
          </button>
        </>
      )}

      {/* Edit form */}
      {editing && (
        <form onSubmit={handleSave} className="space-y-4 p-5 rounded-2xl bg-white/10 border border-white/15">
          <h2 className="text-sm font-semibold text-white">Edit Biometrics</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {fields.map((f) => (
              <div key={f.key}>
                <label className={labelCls}>{f.label}</label>
                <input
                  type={f.type}
                  className={inputCls}
                  placeholder={f.placeholder}
                  value={form[f.key] ?? ''}
                  onChange={(e) => set(f.key, e.target.value)}
                />
              </div>
            ))}
          </div>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded-xl bg-white/20 text-white text-xs font-semibold hover:bg-white/30 transition-all disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              type="button"
              onClick={() => { setEditing(false); setForm(data) }}
              className="px-4 py-2 rounded-xl bg-white/5 text-white/50 text-xs hover:text-white transition-all"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
