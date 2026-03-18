import { useState } from 'react'
import { X } from 'lucide-react'
import { createPlayer } from '../api/players'
import toast from 'react-hot-toast'

const POSITIONS = ['Defender', 'Forward', 'Goalkeeper', 'Midfielder']

export default function AddPlayerModal({ teamId, onClose }) {
  const [form, setForm] = useState({
    full_name: '', position: 'Midfielder', age: '', height_cm: '', weight_kg: '',
    nationality: 'Romanian', status: 'active', team_id: teamId,
  })
  const [saving, setSaving] = useState(false)

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await createPlayer({ ...form, age: +form.age, height_cm: +form.height_cm, weight_kg: +form.weight_kg })
      toast.success('Player added!')
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to add player')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between p-6 border-b border-slate-100">
          <h3 className="font-semibold text-slate-800">Add New Player</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-3">
          <div>
            <label className="label">Full Name</label>
            <input className="input" value={form.full_name} onChange={(e) => set('full_name', e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Position</label>
              <select className="input" value={form.position} onChange={(e) => set('position', e.target.value)}>
                {POSITIONS.map((p) => <option key={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Age</label>
              <input type="number" className="input" min="15" max="45" value={form.age} onChange={(e) => set('age', e.target.value)} required />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Height (cm)</label>
              <input type="number" className="input" value={form.height_cm} onChange={(e) => set('height_cm', e.target.value)} required />
            </div>
            <div>
              <label className="label">Weight (kg)</label>
              <input type="number" className="input" value={form.weight_kg} onChange={(e) => set('weight_kg', e.target.value)} required />
            </div>
          </div>
          <div>
            <label className="label">Nationality</label>
            <input className="input" value={form.nationality} onChange={(e) => set('nationality', e.target.value)} />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
            <button type="submit" className="btn-primary flex-1" disabled={saving}>
              {saving ? 'Saving…' : 'Add Player'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
