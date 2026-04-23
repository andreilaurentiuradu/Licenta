import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import toast from 'react-hot-toast'

const THEMES = {
  football: {
    bg: 'from-emerald-950 via-emerald-900 to-green-800',
    accent: '#34d399',
    label: '⚽ Football',
    ring: 'focus:ring-emerald-500',
    btn: 'bg-emerald-500 hover:bg-emerald-400',
  },
  marathon: {
    bg: 'from-orange-950 via-orange-900 to-red-800',
    accent: '#fb923c',
    label: '🏃 Marathon',
    ring: 'focus:ring-orange-500',
    btn: 'bg-orange-500 hover:bg-orange-400',
  },
}

const DOTS = [
  { top: '8%',  left: '6%',  delay: '0s',    size: 6  },
  { top: '18%', left: '88%', delay: '0.6s',  size: 4  },
  { top: '45%', left: '4%',  delay: '1.1s',  size: 8  },
  { top: '70%', left: '92%', delay: '0.3s',  size: 5  },
  { top: '85%', left: '12%', delay: '0.9s',  size: 4  },
  { top: '60%', left: '80%', delay: '1.4s',  size: 7  },
]

export default function Login() {
  const { login }  = useAuth()
  const navigate   = useNavigate()
  const sport      = localStorage.getItem('selected_sport') || 'football'
  const theme      = THEMES[sport] || THEMES.football

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await login(username, password)
      navigate('/home')
    } catch (err) {
      const desc = err.response?.data?.error_description || err.response?.data?.error || 'Invalid username or password'
      toast.error(desc)
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

      <div className={`min-h-screen bg-gradient-to-br ${theme.bg} flex items-center justify-center p-4 relative overflow-hidden`}>

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
            style={{
              top: d.top, left: d.left,
              width: d.size, height: d.size,
              opacity: 0.12,
              animationDelay: d.delay,
            }}
          />
        ))}

        {/* Card */}
        <div className="form-card relative z-10 w-full max-w-sm">

          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <p className="text-white text-xl font-bold tracking-tight">Sign in</p>
              <p className="text-xs mt-0.5" style={{ color: theme.accent }}>{theme.label}</p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="text-xs text-white/40 hover:text-white/70 transition-colors"
            >
              ← Change sport
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-xs font-medium text-white/60 mb-1.5">Username</label>
              <input
                id="username"
                className={`w-full bg-white/10 border border-white/20 rounded-xl px-4 py-2.5 text-sm text-white placeholder-white/30 outline-none focus:ring-2 ${theme.ring} focus:border-transparent transition-all`}
                placeholder="your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-xs font-medium text-white/60 mb-1.5">Password</label>
              <input
                id="password"
                type="password"
                className={`w-full bg-white/10 border border-white/20 rounded-xl px-4 py-2.5 text-sm text-white placeholder-white/30 outline-none focus:ring-2 ${theme.ring} focus:border-transparent transition-all`}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className={`w-full ${theme.btn} text-white text-sm font-semibold py-2.5 rounded-xl transition-all duration-200 disabled:opacity-50 mt-2`}
            >
              {loading ? 'Signing in…' : 'Sign in →'}
            </button>
          </form>

          <p className="text-center text-xs text-white/40 mt-6">
            No account?{' '}
            <Link to="/register" className="text-white/80 hover:text-white font-medium transition-colors">
              Register
            </Link>
          </p>

          {/* Demo accounts */}
          <div className="mt-6 p-3 rounded-xl bg-white/5 border border-white/10 text-xs text-white/40 space-y-0.5">
            <p className="font-medium text-white/60 mb-1">Demo accounts</p>
            <p>admin_user / admin123 · admin</p>
            <p>coach_user / coach123 · coach</p>
          </div>
        </div>
      </div>
    </>
  )
}
