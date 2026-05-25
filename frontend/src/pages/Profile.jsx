import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

const THEMES = {
  football: { bg: 'from-emerald-950 via-emerald-900 to-green-800', accent: '#34d399', ring: 'focus:ring-emerald-500' },
  marathon: { bg: 'from-orange-950 via-orange-900 to-red-800',     accent: '#fb923c', ring: 'focus:ring-orange-500' },
}

const DOTS = [
  { top: '6%',  left: '5%',  delay: '0s',   size: 5 },
  { top: '22%', left: '91%', delay: '0.9s', size: 6 },
  { top: '54%', left: '2%',  delay: '1.2s', size: 4 },
  { top: '78%', left: '89%', delay: '0.4s', size: 7 },
  { top: '90%', left: '17%', delay: '1.5s', size: 4 },
]

function initials(username) {
  if (!username) return '?'
  return username.slice(0, 2).toUpperCase()
}

function roleLabel(roles) {
  if (roles?.includes('admin'))  return { text: 'Admin',  color: 'bg-purple-500/20 text-purple-300' }
  if (roles?.includes('player')) return { text: 'Player', color: 'bg-amber-500/20 text-amber-300' }
  return { text: 'Coach', color: 'bg-blue-500/20 text-blue-300' }
}

export default function Profile() {
  const { user, logout } = useAuth()
  const navigate         = useNavigate()
  const sport            = localStorage.getItem('selected_sport') || 'football'
  const theme            = THEMES[sport] || THEMES.football
  const role             = roleLabel(user?.roles)

  const handleLogout = () => { logout(); navigate('/') }

  const INFO_ROWS = [
    { label: 'Username', value: user?.username ?? '—' },
    { label: 'Email',    value: user?.email    ?? '—' },
    { label: 'Club',     value: user?.club     ?? '—' },
    { label: 'Sport',    value: sport.charAt(0).toUpperCase() + sport.slice(1) },
    { label: 'Role',     value: role.text },
  ]

  return (
    <>
      <style>{`
        @keyframes float  { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }
        @keyframes slideUp{ from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        @keyframes popIn  { from{opacity:0;transform:scale(0.85)} to{opacity:1;transform:scale(1)} }
        .dot-float  { animation: float 4s ease-in-out infinite; }
        .slide-up   { animation: slideUp 0.5s ease both; }
        .slide-up-2 { animation: slideUp 0.5s ease 0.1s both; }
        .slide-up-3 { animation: slideUp 0.5s ease 0.2s both; }
        .pop-in     { animation: popIn 0.45s ease both; }
      `}</style>

      <div className={`min-h-screen bg-gradient-to-br ${theme.bg} p-6 relative overflow-hidden`}>

        {DOTS.map((d, i) => (
          <div key={i} className="dot-float absolute rounded-full bg-white pointer-events-none"
            style={{ top: d.top, left: d.left, width: d.size, height: d.size, opacity: 0.12, animationDelay: d.delay }}
          />
        ))}

        <div className="relative z-10 max-w-lg mx-auto pt-4">

          {/* Header */}
          <div className="slide-up flex items-center gap-4 mb-10">
            <button onClick={() => navigate('/home')} className="text-white/40 hover:text-white/80 transition-colors text-sm">
              ← Back
            </button>
            <div>
              <h1 className="text-2xl font-bold text-white">Profile</h1>
              <p className="text-xs text-white/40 mt-0.5">Account details</p>
            </div>
          </div>

          {/* Avatar + name */}
          <div className="pop-in flex flex-col items-center mb-8">
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center text-2xl font-bold text-white mb-4 border-2 border-white/20"
              style={{ background: `${theme.accent}30` }}
            >
              <span style={{ color: theme.accent }}>{initials(user?.username)}</span>
            </div>
            <h2 className="text-xl font-bold text-white">{user?.username}</h2>
            <span className={`mt-2 text-xs font-semibold px-3 py-1 rounded-full ${role.color}`}>
              {role.text}
            </span>
          </div>

          {/* Info rows */}
          <div className="slide-up-2 space-y-2 mb-8">
            <p className="text-xs font-semibold text-white/40 uppercase tracking-widest mb-4">Account info</p>
            {INFO_ROWS.map((row) => (
              <div key={row.label} className="flex items-center justify-between px-5 py-4 rounded-2xl bg-white/8 border border-white/10">
                <p className="text-xs text-white/40">{row.label}</p>
                <p className="text-sm font-medium text-white">{row.value}</p>
              </div>
            ))}
          </div>

          {/* Roles */}
          <div className="slide-up-3 mb-8">
            <p className="text-xs font-semibold text-white/40 uppercase tracking-widest mb-4">Assigned roles</p>
            <div className="flex flex-wrap gap-2 px-1">
              {(user?.roles ?? [])
                .filter(r => !['default-roles-sport-analytics', 'offline_access', 'uma_authorization'].includes(r))
                .map(r => (
                  <span key={r} className="text-xs font-medium px-3 py-1.5 rounded-full bg-white/10 border border-white/15 text-white/70">
                    {r}
                  </span>
                ))
              }
            </div>
          </div>

          {/* Sign out */}
          <div className="slide-up-3 text-center">
            <button
              onClick={handleLogout}
              className="text-xs text-white/30 hover:text-white/60 transition-colors"
            >
              Sign out
            </button>
          </div>

        </div>
      </div>
    </>
  )
}
