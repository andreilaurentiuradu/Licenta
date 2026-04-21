import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import toast from 'react-hot-toast'

const SPORT_LABEL = { football: '⚽ Football', marathon: '🏃 Marathon' }

export default function Login() {
  const { login }  = useAuth()
  const navigate   = useNavigate()
  const sport      = localStorage.getItem('selected_sport')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await login(username, password)
      navigate('/home')
    } catch {
      toast.error('Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 w-full max-w-sm p-8">

        {/* Sport badge + back */}
        <div className="flex items-center justify-between mb-6">
          {sport && (
            <span className="text-xs font-medium bg-slate-100 text-slate-600 px-3 py-1 rounded-full">
              {SPORT_LABEL[sport]}
            </span>
          )}
          <button
            onClick={() => navigate('/')}
            className="text-xs text-slate-400 hover:text-slate-600 ml-auto"
          >
            ← Change sport
          </button>
        </div>

        <h1 className="text-xl font-semibold text-slate-800 mb-1">Sign in</h1>
        <p className="text-sm text-slate-400 mb-6">SportAnalytics Platform</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Username</label>
            <input
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Password</label>
            <input
              type="password"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-slate-800 text-white text-sm font-medium py-2 rounded-lg hover:bg-slate-700 transition-colors disabled:opacity-50"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-xs text-slate-400 mt-5">
          No account?{' '}
          <Link to="/register" className="text-slate-700 hover:underline font-medium">Register</Link>
        </p>

        <div className="mt-5 p-3 bg-slate-50 rounded-lg text-xs text-slate-400 space-y-0.5">
          <p className="font-medium text-slate-500 mb-1">Demo accounts</p>
          <p>admin_user / admin123 &nbsp;·&nbsp; role: admin</p>
          <p>coach_user / coach123 &nbsp;·&nbsp; role: coach</p>
        </div>
      </div>
    </div>
  )
}
