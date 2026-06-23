import { Outlet, useNavigate, useParams, NavLink, useSearchParams, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import ThemedBackground from '../components/ThemedBackground'

const TABS = [
  { path: 'biometrics',      label: 'Biometrics'      },
  { path: 'training',        label: 'Training'        },
  { path: 'physical',        label: 'Physical'        },
  { path: 'injuries',        label: 'Injuries'        },
  { path: 'wellness',        label: 'Wellness'        },
  { path: 'recommendations', label: 'Recommendations' },
]

// Map the active tab to its background motif.
const BG_VARIANTS = {
  biometrics:      'body',
  training:        'strength',
  physical:        'health',
  injuries:        'medical',
  wellness:        'wellness',
  recommendations: 'spark',
}

function pickRole(roles) {
  if (roles?.includes('admin'))  return 'admin'
  if (roles?.includes('coach'))  return 'coach'
  return 'player'
}

export default function PlayerLayout() {
  const { id }        = useParams()
  const { user }      = useAuth()
  const navigate      = useNavigate()
  const location      = useLocation()
  const [params, setParams] = useSearchParams()

  const role     = pickRole(user?.roles)
  const isPlayer = role === 'player'
  const accent   = 'from-emerald-950 via-emerald-900 to-green-800'

  const activeTab = TABS.find((t) => location.pathname.endsWith(`/${t.path}`))?.path
  const bgVariant = BG_VARIANTS[activeTab] || 'spark'
  // Period filter only applies to time-series tabs; Biometrics/Recommendations have fixed data.
  const showPeriod = ['training', 'physical', 'injuries', 'wellness'].includes(activeTab)

  const fromDate = params.get('from') || ''
  const toDate   = params.get('to')   || ''

  const setDate = (key, val) => {
    const next = new URLSearchParams(params)
    if (val) next.set(key, val)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  const backTarget = isPlayer ? '/home' : '/players'

  return (
    <div className={`min-h-screen bg-gradient-to-br ${accent} flex flex-col relative overflow-hidden`}>
      {/* Theme-specific decorative background, switches per tab */}
      <ThemedBackground variant={bgVariant} />

      {/* Header */}
      <div className="relative z-10 px-4 sm:px-6 pt-5 pb-0 border-b border-white/10">
        <div className="max-w-3xl lg:max-w-6xl mx-auto">

          {/* Back + title */}
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => navigate(backTarget)}
              className="text-white/50 hover:text-white transition-colors text-sm shrink-0"
            >
              ← {isPlayer ? 'Home' : 'Players'}
            </button>
            <h1 className="text-lg font-bold text-white truncate">
              {isPlayer ? 'My Stats' : `Player · ${id.slice(0, 8)}…`}
            </h1>
          </div>

          {/* Date range — only on time-series tabs */}
          {showPeriod && (
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <span className="text-xs text-white/40">Period:</span>
            <div className="flex items-center gap-2 flex-wrap">
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setDate('from', e.target.value)}
                className="bg-white/10 border border-white/20 rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:ring-2 focus:ring-white/30 w-36"
              />
              <span className="text-xs text-white/40">–</span>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setDate('to', e.target.value)}
                className="bg-white/10 border border-white/20 rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:ring-2 focus:ring-white/30 w-36"
              />
              {(fromDate || toDate) && (
                <button
                  onClick={() => { setDate('from', ''); setDate('to', '') }}
                  className="text-xs text-white/40 hover:text-white transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
          )}

          {/* Tabs — horizontal scroll on mobile, visible all on desktop */}
          <div className="relative">
            <nav className="flex gap-1 overflow-x-auto scrollbar-hide pb-0">
              {TABS.map((t) => (
                <NavLink
                  key={t.path}
                  to={`/players/${id}/${t.path}?${params.toString()}`}
                  className={({ isActive }) =>
                    `px-3 sm:px-4 py-2.5 rounded-t-xl text-xs font-medium whitespace-nowrap transition-all border-b-2 ${
                      isActive
                        ? 'bg-white/15 text-white border-emerald-400'
                        : 'text-white/50 hover:text-white hover:bg-white/10 border-transparent'
                    }`
                  }
                >
                  {t.label}
                </NavLink>
              ))}
            </nav>
            {/* Right fade hint — visible only when tabs overflow */}
            <div className="pointer-events-none absolute right-0 top-0 h-full w-8 bg-gradient-to-l from-emerald-950/80 to-transparent sm:hidden" />
          </div>
        </div>
      </div>

      {/* Page content */}
      <div className="relative z-10 flex-1 px-4 sm:px-6 py-5">
        <div className="max-w-3xl lg:max-w-6xl mx-auto">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
