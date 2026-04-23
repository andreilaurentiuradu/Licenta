import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

const THEMES = {
  football: { bg: 'from-emerald-950 via-emerald-900 to-green-800', accent: '#34d399', label: '⚽ Football' },
  marathon: { bg: 'from-orange-950 via-orange-900 to-red-800',     accent: '#fb923c', label: '🏃 Marathon' },
}

const DOTS = [
  { top: '8%',  left: '5%',  delay: '0s',   size: 5 },
  { top: '20%', left: '91%', delay: '0.8s', size: 7 },
  { top: '50%', left: '3%',  delay: '1.3s', size: 4 },
  { top: '72%', left: '88%', delay: '0.5s', size: 6 },
  { top: '88%', left: '15%', delay: '1s',   size: 5 },
  { top: '38%', left: '94%', delay: '1.6s', size: 4 },
]

const BASE_CARDS = [
  { to: '/profile',  icon: '👤', title: 'Profile',  desc: 'Account details and assigned roles' },
  { to: '/support',  icon: '🛟', title: 'Support',  desc: 'Documentation, FAQs and contact' },
  { to: '/feedback', icon: '💬', title: 'Feedback', desc: 'Rate the platform and share thoughts' },
]

const ADMIN_CARD = {
  to: '/admin/users', icon: '🛡️', title: 'User Management', desc: 'Create coaches, players and admins',
}

const ROLE_BADGE = {
  admin:  { text: 'Admin',  class: 'bg-purple-500/20 text-purple-300' },
  coach:  { text: 'Coach',  class: 'bg-blue-500/20 text-blue-300' },
  player: { text: 'Player', class: 'bg-amber-500/20 text-amber-300' },
}

const ROLE_DESC = {
  admin:  'Administrator access · Full platform control',
  coach:  'Coach access · Player analytics coming in Sprint 2',
  player: 'Player access · Personal stats and training data',
}

function pickRole(roles) {
  if (roles?.includes('admin'))  return 'admin'
  if (roles?.includes('coach'))  return 'coach'
  if (roles?.includes('player')) return 'player'
  return 'coach'
}

export default function Home() {
  const { user, logout } = useAuth()
  const navigate         = useNavigate()
  const sport            = localStorage.getItem('selected_sport') || 'football'
  const theme            = THEMES[sport] || THEMES.football
  const role             = pickRole(user?.roles)
  const isAdmin          = role === 'admin'
  const roleBadge        = ROLE_BADGE[role]
  const navCards         = isAdmin ? [...BASE_CARDS, ADMIN_CARD] : BASE_CARDS

  const handleLogout = () => { logout(); navigate('/') }

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
        .dot-float  { animation: float 4s ease-in-out infinite; }
        .slide-up   { animation: slideUp 0.5s ease both; }
        .slide-up-2 { animation: slideUp 0.5s ease 0.15s both; }
        .slide-up-3 { animation: slideUp 0.5s ease 0.3s both; }
        .nav-card:hover { transform: translateY(-4px); background: rgba(255,255,255,0.15); }
        .nav-card { transition: transform 0.2s ease, background 0.2s ease; }
      `}</style>

      <div className={`min-h-screen bg-gradient-to-br ${theme.bg} flex flex-col items-center justify-center p-6 relative overflow-hidden`}>

        {/* Grid lines */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute w-full h-px bg-white opacity-5" style={{ top: '25%' }} />
          <div className="absolute w-full h-px bg-white opacity-5" style={{ top: '50%' }} />
          <div className="absolute w-full h-px bg-white opacity-5" style={{ top: '75%' }} />
          <div className="absolute h-full w-px bg-white opacity-5" style={{ left: '33%' }} />
          <div className="absolute h-full w-px bg-white opacity-5" style={{ left: '66%' }} />
        </div>

        {/* Floating dots */}
        {DOTS.map((d, i) => (
          <div key={i} className="dot-float absolute rounded-full bg-white pointer-events-none"
            style={{ top: d.top, left: d.left, width: d.size, height: d.size, opacity: 0.12, animationDelay: d.delay }}
          />
        ))}

        <div className="relative z-10 w-full max-w-md">

          {/* Sport badge */}
          <div className="slide-up flex items-center justify-between mb-10">
            <span className="text-xs font-medium px-3 py-1 rounded-full bg-white/10 text-white/70">
              {theme.label}
            </span>
            <span className={`text-xs font-semibold px-3 py-1 rounded-full ${roleBadge.class}`}>
              {roleBadge.text}
            </span>
          </div>

          {/* Welcome */}
          <div className="slide-up-2 mb-10">
            <h1 className="text-3xl font-bold text-white tracking-tight">
              Welcome back,<br />
              <span style={{ color: theme.accent }}>{user?.username}</span>
            </h1>
            <p className="text-white/40 text-sm mt-2">
              {ROLE_DESC[role]}
            </p>
          </div>

          {/* Navigation cards */}
          <div className="slide-up-3 mb-10">
            {navCards.length % 2 === 0 ? (
              <div className="grid grid-cols-2 gap-3">
                {navCards.map((card) => (
                  <button
                    key={card.to}
                    onClick={() => navigate(card.to)}
                    className="nav-card text-left p-5 rounded-2xl bg-white/10 border border-white/15"
                  >
                    <span className="text-2xl block mb-3">{card.icon}</span>
                    <p className="text-sm font-semibold text-white">{card.title}</p>
                    <p className="text-xs text-white/40 mt-0.5">{card.desc}</p>
                  </button>
                ))}
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3 mb-3">
                  {navCards.slice(0, 2).map((card) => (
                    <button
                      key={card.to}
                      onClick={() => navigate(card.to)}
                      className="nav-card text-left p-5 rounded-2xl bg-white/10 border border-white/15"
                    >
                      <span className="text-2xl block mb-3">{card.icon}</span>
                      <p className="text-sm font-semibold text-white">{card.title}</p>
                      <p className="text-xs text-white/40 mt-0.5">{card.desc}</p>
                    </button>
                  ))}
                </div>
                {navCards.slice(2).map((card) => (
                  <button
                    key={card.to}
                    onClick={() => navigate(card.to)}
                    className="nav-card w-full text-left p-5 rounded-2xl bg-white/10 border border-white/15"
                  >
                    <span className="text-2xl block mb-3">{card.icon}</span>
                    <p className="text-sm font-semibold text-white">{card.title}</p>
                    <p className="text-xs text-white/40 mt-0.5">{card.desc}</p>
                  </button>
                ))}
              </>
            )}
          </div>

          {/* Sign out */}
          <div className="text-center">
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
