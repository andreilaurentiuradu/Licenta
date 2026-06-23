import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { triggerFLRound, getFlStatus, getFlClubs, getRiskRanking } from '../api/fl'
import toast from 'react-hot-toast'

const THEMES = {
  football: { bg: 'from-emerald-950 via-emerald-900 to-green-800', accent: '#34d399', label: '⚽ Football' },
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

const ADMIN_USERS_CARD = {
  to: '/admin/users', icon: '👥', title: 'All Users', desc: 'View and delete platform accounts',
}

const ADMIN_CREATE_CARD = {
  to: '/admin/create-user', icon: '🛡️', title: 'Create User', desc: 'Add coaches, players and admins',
}

const ADMIN_FEEDBACK_CARD = {
  to: '/admin/feedback', icon: '💬', title: 'View Feedback', desc: 'Read feedback from players and coaches',
}

const BASE_CARDS_NO_FEEDBACK = BASE_CARDS.filter(c => c.to !== '/feedback')

const COACH_PLAYERS_CARD = {
  to: '/players', icon: '📊', title: 'Players', desc: 'View and manage player metrics',
}

const PLAYER_STATS_CARD = (sub) => ({
  to: `/players/${sub}/biometrics`, icon: '📊', title: 'My Stats', desc: 'Biometrics, training and wellness data',
})

const ROLE_BADGE = {
  admin:  { text: 'Admin',  class: 'bg-purple-500/20 text-purple-300' },
  coach:  { text: 'Coach',  class: 'bg-blue-500/20 text-blue-300' },
  player: { text: 'Player', class: 'bg-amber-500/20 text-amber-300' },
}

const ROLE_DESC = {
  admin:  (club) => `Administrator access · Full platform control${club ? ` · ${club}` : ''}`,
  coach:  (club) => `Coach · ${club || 'No club assigned'} · Manage players & FL training`,
  player: (club) => `Player · ${club || 'No club assigned'} · Personal stats & recommendations`,
}

function pickRole(roles) {
  if (roles?.includes('admin'))  return 'admin'
  if (roles?.includes('coach'))  return 'coach'
  if (roles?.includes('player')) return 'player'
  return 'coach'
}

function FLPanel({ club }) {
  const [loading,  setLoading]  = useState(false)
  const [result,   setResult]   = useState(null)
  const [status,   setStatus]   = useState(null)

  useEffect(() => {
    getFlStatus()
      .then(r => setStatus(r.data))
      .catch(() => {})
  }, [])

  const handleTrain = async () => {
    setLoading(true)
    setResult(null)
    try {
      const { data } = await triggerFLRound()
      setResult(data)
      if (data.warning) toast(data.warning, { icon: '⚠️', duration: 7000 })
      else toast.success('FL training round completed')
      // Refresh status after training
      getFlStatus().then(r => setStatus(r.data)).catch(() => {})
    } catch {
      toast.error('Failed to start training round')
    } finally {
      setLoading(false)
    }
  }

  const round = status?.round      ?? result?.fl_round          ?? null

  return (
    <div className="mb-6 p-5 rounded-2xl bg-white/8 border border-white/10">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-sm font-semibold text-white">Federated Learning</p>
          <p className="text-xs text-white/40 mt-0.5">
            {club ? `${club} · ` : ''}Injury-prediction model · raw data never leaves the club.
          </p>
        </div>
        <button
          onClick={handleTrain}
          disabled={loading}
          className="shrink-0 px-4 py-2 rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 text-white text-xs font-semibold transition-all"
        >
          {loading ? 'Training…' : 'Start round →'}
        </button>
      </div>

      {/* Global model stats (model-quality metrics are admin-only) */}
      {status?.ready && (
        <div className="mt-4 grid grid-cols-2 gap-2 sm:gap-3 text-center">
          <div className="p-2 rounded-lg bg-white/5">
            <p className="text-base font-bold text-white">{round ?? '—'}</p>
            <p className="text-xs text-white/40">Round</p>
          </div>
          <div className="p-2 rounded-lg bg-white/5">
            <p className="text-base font-bold text-white">{status.clubs_count ?? 0}</p>
            <p className="text-xs text-white/40">Clubs</p>
          </div>
        </div>
      )}

      {!status?.ready && status !== null && (
        <p className="mt-3 text-xs text-white/30">
          Model not initialised — place data.csv in backend/models/ and restart.
        </p>
      )}

      {/* Training result */}
      {result && (
        <div className="mt-3 space-y-2">
          {result.warning && (
            <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20">
              <span className="text-amber-400 text-xs mt-0.5">⚠</span>
              <p className="text-xs text-amber-300">{result.warning}</p>
            </div>
          )}
          {result.trained && !result.warning && (
            <p className="text-xs text-emerald-400">
              Round {result.fl_round} complete · {result.players_in_round} players
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// Admin-only: cross-validated model metrics + per-club FL training controls.
function AdminFLPanel() {
  const [status, setStatus] = useState(null)
  const [clubs,  setClubs]  = useState([])
  const [busy,   setBusy]   = useState(null)

  const refresh = () => {
    getFlStatus().then(r => setStatus(r.data)).catch(() => {})
    getFlClubs().then(r => setClubs(r.data)).catch(() => {})
  }
  useEffect(() => { refresh() }, [])

  const runClub = async (club) => {
    setBusy(club)
    try {
      const { data } = await triggerFLRound(club)
      if (data.trained) toast.success(`Round ${data.fl_round} complete · ${club}`)
      else toast(data.warning || 'FL update skipped', { icon: 'ℹ️' })
      refresh()
    } catch {
      toast.error('Failed to run FL round')
    } finally {
      setBusy(null)
    }
  }

  if (!status?.ready) return null
  const pct  = status.accuracy != null ? `${(status.accuracy * 100).toFixed(1)}%` : '—'
  const rec  = status.recall   != null ? status.recall.toFixed(2) : '—'
  const loss = status.loss     != null ? status.loss.toFixed(3)   : '—'

  return (
    <div className="mb-6 p-5 rounded-2xl bg-white/8 border border-white/10">
      <p className="text-sm font-semibold text-white">Federated Learning · Admin</p>
      <p className="text-xs text-white/40 mt-0.5">
        Run a training round per club and watch the global round update · raw data never leaves the club.
      </p>

      {/* Global model stats + admin-only quality metrics */}
      <div className="mt-4 grid grid-cols-2 sm:grid-cols-5 gap-2 sm:gap-3 text-center">
        <div className="p-2 rounded-lg bg-white/5">
          <p className="text-base font-bold text-white">{status.round ?? '—'}</p>
          <p className="text-xs text-white/40">Round</p>
        </div>
        <div className="p-2 rounded-lg bg-white/5">
          <p className="text-base font-bold text-white">{status.clubs_count ?? 0}</p>
          <p className="text-xs text-white/40">Clubs</p>
        </div>
        <div className="p-2 rounded-lg bg-white/5">
          <p className="text-base font-bold text-indigo-300">{pct}</p>
          <p className="text-xs text-white/40">Accuracy (CV)</p>
        </div>
        <div className="p-2 rounded-lg bg-white/5">
          <p className="text-base font-bold text-indigo-300">{rec}</p>
          <p className="text-xs text-white/40">Recall</p>
        </div>
        <div className="p-2 rounded-lg bg-white/5">
          <p className="text-base font-bold text-indigo-300">{loss}</p>
          <p className="text-xs text-white/40">Log loss</p>
        </div>
      </div>

      {/* Per-club training */}
      <div className="mt-4 space-y-2">
        {clubs.map((c) => (
          <div key={c.club} className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-white/5 border border-white/10">
            <div className="min-w-0">
              <p className="text-sm text-white truncate">{c.club}</p>
              <p className="text-xs text-white/40">
                {c.players} players · {c.n_samples} samples{c.updated_at ? ` · ${c.updated_at.slice(0, 10)}` : ''}
              </p>
            </div>
            <button
              onClick={() => runClub(c.club)}
              disabled={busy !== null}
              className="shrink-0 px-3 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-400 text-white text-xs font-semibold transition-all disabled:opacity-50"
            >
              {busy === c.club ? 'Running…' : 'Run round →'}
            </button>
          </div>
        ))}
        {clubs.length === 0 && (
          <p className="text-white/30 text-xs text-center py-3">No clubs with players yet.</p>
        )}
      </div>
    </div>
  )
}

const RISK_CONFIG = {
  high:   { label: 'High',   bg: 'bg-red-500/15',    border: 'border-red-500/30',    text: 'text-red-400',    dot: 'bg-red-400' },
  medium: { label: 'Medium', bg: 'bg-amber-500/15',  border: 'border-amber-500/30',  text: 'text-amber-400',  dot: 'bg-amber-400' },
  low:    { label: 'Low',    bg: 'bg-emerald-500/15', border: 'border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-400' },
}

function RiskPanel({ navigate }) {
  const [players, setPlayers] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getRiskRanking()
      .then(r => setPlayers(r.data))
      .catch(() => setPlayers([]))
      .finally(() => setLoading(false))
  }, [])

  const high   = players?.filter(p => p.risk === 'high')   ?? []
  const medium = players?.filter(p => p.risk === 'medium') ?? []

  if (loading) return (
    <div className="mb-6 p-5 rounded-2xl bg-white/8 border border-white/10">
      <p className="text-xs text-white/30">Loading risk data…</p>
    </div>
  )

  if (!players?.length) return null

  return (
    <div className="mb-6 rounded-2xl bg-white/8 border border-white/10 overflow-hidden">
      {/* Header */}
      <div className="px-5 pt-4 pb-3 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-white">Injury Risk Ranking</p>
          <p className="text-xs text-white/40 mt-0.5">{players.length} players · sorted by risk</p>
        </div>
        {high.length > 0 && (
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-red-500/20 text-red-400">
            {high.length} high risk
          </span>
        )}
      </div>

      {/* Alert banner for high-risk players */}
      {high.length > 0 && (
        <div className="mx-5 mb-3 p-3 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-2">
          <span className="text-red-400 text-sm mt-0.5">⚠</span>
          <p className="text-xs text-red-300 leading-relaxed">
            <span className="font-semibold">{high.map(p => p.username).join(', ')}</span>
            {high.length === 1 ? ' requires' : ' require'} immediate attention — injury risk is high.
          </p>
        </div>
      )}

      {/* Player list */}
      <div className="px-3 pb-3 space-y-1.5">
        {players.map((p, i) => {
          const cfg = RISK_CONFIG[p.risk] ?? RISK_CONFIG.low
          return (
            <button
              key={p.user_id}
              onClick={() => navigate(`/players/${p.user_id}/biometrics`)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border ${cfg.bg} ${cfg.border} hover:opacity-80 transition-opacity text-left`}
            >
              <span className="text-xs text-white/30 w-4 shrink-0">{i + 1}</span>
              <span className={`w-2 h-2 rounded-full shrink-0 ${cfg.dot}`} />
              <span className="flex-1 text-sm font-medium text-white truncate">{p.username}</span>
              <span className="text-xs text-white/40 shrink-0">{p.position ?? '—'}</span>
              <span className={`text-xs font-semibold shrink-0 ${cfg.text}`}>
                {cfg.label} · {(p.probability * 100).toFixed(0)}%
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function Home() {
  const { user, logout } = useAuth()
  const navigate         = useNavigate()
  const sport            = localStorage.getItem('selected_sport') || 'football'
  const theme            = THEMES[sport] || THEMES.football
  const role             = pickRole(user?.roles)
  const isAdmin          = role === 'admin'
  const isCoach          = role === 'coach'
  const isPlayer         = role === 'player'
  const club             = user?.club
  const roleBadge        = ROLE_BADGE[role]
  const navCards         = isAdmin
    ? [...BASE_CARDS_NO_FEEDBACK, ADMIN_USERS_CARD, ADMIN_CREATE_CARD, ADMIN_FEEDBACK_CARD]
    : isCoach
    ? [...BASE_CARDS, COACH_PLAYERS_CARD]
    : isPlayer
    ? [...BASE_CARDS, PLAYER_STATS_CARD(user?.sub)]
    : BASE_CARDS

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

      <div className={`min-h-screen bg-gradient-to-br ${theme.bg} flex flex-col items-center justify-center p-4 sm:p-6 relative overflow-hidden`}>

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

        <div className="relative z-10 w-full max-w-md lg:max-w-4xl">

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
              {ROLE_DESC[role](club)}
            </p>
          </div>

          {/* Navigation cards */}
          <div className="slide-up-3 mb-10">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {navCards.map((card) => (
                <button
                  key={card.to}
                  onClick={() => navigate(card.to)}
                  className="nav-card text-left p-4 sm:p-5 rounded-2xl bg-white/10 border border-white/15"
                >
                  <span className="text-2xl block mb-3">{card.icon}</span>
                  <p className="text-sm font-semibold text-white">{card.title}</p>
                  <p className="text-xs text-white/40 mt-0.5">{card.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* FL training + metrics — admin only */}
          {isAdmin && <AdminFLPanel />}

          {/* FL panel + Risk ranking — coach only, side-by-side on desktop */}
          {isCoach && (
            <div className="lg:grid lg:grid-cols-2 lg:gap-6">
              <FLPanel club={club} />
              <RiskPanel navigate={navigate} />
            </div>
          )}

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
