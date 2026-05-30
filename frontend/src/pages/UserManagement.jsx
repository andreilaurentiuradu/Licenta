import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { adminCreateUser } from '../api/auth'

const THEMES = {
  football: { bg: 'from-emerald-950 via-emerald-900 to-green-800', accent: '#34d399', ring: 'focus:ring-emerald-500', btn: 'bg-emerald-500 hover:bg-emerald-400' },
}

const DOTS = [
  { top: '7%',  left: '5%',  delay: '0s',   size: 5 },
  { top: '22%', left: '91%', delay: '0.8s', size: 6 },
  { top: '55%', left: '3%',  delay: '1.2s', size: 4 },
  { top: '78%', left: '90%', delay: '0.4s', size: 7 },
  { top: '90%', left: '18%', delay: '1.5s', size: 4 },
]

const ROLE_BADGES = {
  admin:  'bg-purple-500/20 text-purple-300',
  coach:  'bg-blue-500/20 text-blue-300',
  player: 'bg-amber-500/20 text-amber-300',
}

export default function UserManagement() {
  const navigate = useNavigate()
  const sport    = localStorage.getItem('selected_sport') || 'football'
  const theme    = THEMES[sport] || THEMES.football

  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    username: '', email: '', password: '', confirm: '', role: 'coach', club: '',
  })

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password !== form.confirm) {
      toast.error('Passwords do not match')
      return
    }
    setLoading(true)
    try {
      await adminCreateUser({
        username: form.username,
        email:    form.email,
        password: form.password,
        role:     form.role,
        club:     form.club || undefined,
      })
      toast.success(`${form.role.charAt(0).toUpperCase() + form.role.slice(1)} "${form.username}" created!`)
      setForm({ username: '', email: '', password: '', confirm: '', role: 'coach', club: '' })
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to create user')
    } finally {
      setLoading(false)
    }
  }

  const inputClass = `w-full bg-white/10 border border-white/20 rounded-xl px-4 py-2.5 text-sm text-white placeholder-white/30 outline-none focus:ring-2 ${theme.ring} focus:border-transparent transition-all`

  return (
    <>
      <style>{`
        @keyframes float  { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }
        @keyframes slideUp{ from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        .dot-float  { animation: float 4s ease-in-out infinite; }
        .slide-up   { animation: slideUp 0.5s ease both; }
        .slide-up-2 { animation: slideUp 0.5s ease 0.1s both; }
      `}</style>

      <div className={`min-h-screen bg-gradient-to-br ${theme.bg} p-6 relative overflow-hidden`}>

        {DOTS.map((d, i) => (
          <div key={i} className="dot-float absolute rounded-full bg-white pointer-events-none"
            style={{ top: d.top, left: d.left, width: d.size, height: d.size, opacity: 0.12, animationDelay: d.delay }}
          />
        ))}

        <div className="relative z-10 max-w-lg mx-auto pt-4">

          <div className="slide-up flex items-center gap-4 mb-10">
            <button onClick={() => navigate('/home')} className="text-white/40 hover:text-white/80 transition-colors text-sm">
              ← Back
            </button>
            <div>
              <h1 className="text-2xl font-bold text-white">User Management</h1>
              <p className="text-xs text-white/40 mt-0.5">Admin — create users of any role</p>
            </div>
          </div>

          <div className="slide-up-2 p-6 rounded-2xl bg-white/8 border border-white/10">
            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label htmlFor="username" className="block text-xs font-medium text-white/60 mb-1.5">Username</label>
                <input
                  id="username"
                  className={inputClass}
                  placeholder="username"
                  value={form.username}
                  onChange={(e) => set('username', e.target.value)}
                  required minLength={3}
                />
              </div>
              <div>
                <label htmlFor="email" className="block text-xs font-medium text-white/60 mb-1.5">Email</label>
                <input
                  id="email"
                  type="email"
                  className={inputClass}
                  placeholder="user@example.com"
                  value={form.email}
                  onChange={(e) => set('email', e.target.value)}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="password" className="block text-xs font-medium text-white/60 mb-1.5">Password</label>
                  <input
                    id="password"
                    type="password"
                    className={inputClass}
                    placeholder="••••••••"
                    value={form.password}
                    onChange={(e) => set('password', e.target.value)}
                    required minLength={6}
                  />
                </div>
                <div>
                  <label htmlFor="confirm" className="block text-xs font-medium text-white/60 mb-1.5">Confirm</label>
                  <input
                    id="confirm"
                    type="password"
                    className={inputClass}
                    placeholder="••••••••"
                    value={form.confirm}
                    onChange={(e) => set('confirm', e.target.value)}
                    required
                  />
                </div>
              </div>
              <div>
                <label htmlFor="club" className="block text-xs font-medium text-white/60 mb-1.5">Club name</label>
                <input
                  id="club"
                  className={inputClass}
                  placeholder="e.g. FC Demo"
                  value={form.club}
                  onChange={(e) => set('club', e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="role" className="block text-xs font-medium text-white/60 mb-1.5">Role</label>
                <select
                  id="role"
                  className={inputClass + ' bg-white/10'}
                  value={form.role}
                  onChange={(e) => set('role', e.target.value)}
                >
                  <option value="coach"  className="bg-slate-900">Coach</option>
                  <option value="player" className="bg-slate-900">Player</option>
                  <option value="admin"  className="bg-slate-900">Admin</option>
                </select>
                <p className="mt-2 text-xs">
                  <span className={`px-2 py-0.5 rounded-full ${ROLE_BADGES[form.role]}`}>{form.role}</span>
                </p>
              </div>
              <button
                type="submit"
                disabled={loading}
                className={`w-full ${theme.btn} text-white text-sm font-semibold py-2.5 rounded-xl transition-all duration-200 disabled:opacity-50 mt-2`}
              >
                {loading ? 'Creating user…' : 'Create user →'}
              </button>
            </form>
          </div>

        </div>
      </div>
    </>
  )
}
