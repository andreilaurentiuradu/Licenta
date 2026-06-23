import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register } from '../api/auth'
import toast from 'react-hot-toast'

const DOTS = [
  { top: '10%', left: '90%', delay: '0s',   size: 5 },
  { top: '25%', left: '5%',  delay: '0.7s', size: 7 },
  { top: '55%', left: '93%', delay: '1.2s', size: 4 },
  { top: '75%', left: '8%',  delay: '0.4s', size: 6 },
  { top: '88%', left: '85%', delay: '1s',   size: 5 },
  { top: '40%', left: '3%',  delay: '1.5s', size: 4 },
]

const inputClass = 'w-full bg-white/10 border border-white/20 rounded-xl px-4 py-2.5 text-sm text-white placeholder-white/30 outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all'

export default function Register() {
  const navigate = useNavigate()

  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    username: '', email: '', password: '', confirm: '', role: 'coach', club: '', sport: 'football',
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
      localStorage.setItem('selected_sport', form.sport)
      await register({ username: form.username, email: form.email, password: form.password, role: form.role, club: form.club || undefined })
      toast.success('Account created! Please sign in.')
      navigate('/login')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50%       { transform: translateY(-14px); }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .dot-float { animation: float 4s ease-in-out infinite; }
        .form-card  { animation: slideUp 0.5s ease both; }
      `}</style>

      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 flex items-center justify-center p-4 sm:p-6 relative overflow-hidden">

        {/* Decorative lines */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute w-full h-px bg-white opacity-5" style={{ top: '25%' }} />
          <div className="absolute w-full h-px bg-white opacity-5" style={{ top: '50%' }} />
          <div className="absolute w-full h-px bg-white opacity-5" style={{ top: '75%' }} />
          <div className="absolute h-full w-px bg-white opacity-5" style={{ left: '33%' }} />
          <div className="absolute h-full w-px bg-white opacity-5" style={{ left: '66%' }} />
        </div>

        {/* Floating dots */}
        {DOTS.map((d, i) => (
          <div
            key={i}
            className="dot-float absolute rounded-full bg-white pointer-events-none"
            style={{ top: d.top, left: d.left, width: d.size, height: d.size, opacity: 0.08, animationDelay: d.delay }}
          />
        ))}

        {/* Card */}
        <div className="form-card relative z-10 w-full max-w-sm sm:max-w-md">

          {/* Header */}
          <div className="mb-8 text-center">
            <p className="text-2xl font-bold text-white tracking-tight">LawrAnalyzer</p>
            <p className="text-xs mt-1 text-white/40">Create your account</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label htmlFor="username" className="block text-xs font-medium text-white/60 mb-1.5">Username</label>
              <input
                id="username"
                className={inputClass}
                placeholder="your username"
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
                placeholder="you@example.com"
                value={form.email}
                onChange={(e) => set('email', e.target.value)}
                required
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="role" className="block text-xs font-medium text-white/60 mb-1.5">Role</label>
                <select
                  id="role"
                  className={inputClass + ' bg-slate-900'}
                  value={form.role}
                  onChange={(e) => set('role', e.target.value)}
                >
                  <option value="coach"  className="bg-slate-900">Coach</option>
                  <option value="player" className="bg-slate-900">Player</option>
                </select>
              </div>
              <div>
                <label htmlFor="sport" className="block text-xs font-medium text-white/60 mb-1.5">Sport</label>
                <select
                  id="sport"
                  className={inputClass + ' bg-slate-900'}
                  value={form.sport}
                  onChange={(e) => set('sport', e.target.value)}
                >
                  <option value="football" className="bg-slate-900">⚽ Football</option>
                </select>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold py-2.5 rounded-xl transition-all duration-200 disabled:opacity-50 mt-1"
            >
              {loading ? 'Creating account…' : 'Create account →'}
            </button>
          </form>

          <p className="text-center text-xs text-white/40 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-white/80 hover:text-white font-medium transition-colors">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </>
  )
}
