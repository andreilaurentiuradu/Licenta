import { Outlet, useNavigate, useParams, NavLink, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const TABS = [
  { path: 'biometrics',      label: 'Biometrics'      },
  { path: 'training',        label: 'Training'        },
  { path: 'physical',        label: 'Physical'        },
  { path: 'injuries',        label: 'Injuries'        },
  { path: 'wellness',        label: 'Wellness'        },
  { path: 'recommendations', label: 'Recommendations' },
]

function pickRole(roles) {
  if (roles?.includes('admin'))  return 'admin'
  if (roles?.includes('coach'))  return 'coach'
  return 'player'
}

export default function PlayerLayout() {
  const { id }        = useParams()
  const { user }      = useAuth()
  const navigate      = useNavigate()
  const [params, setParams] = useSearchParams()

  const role      = pickRole(user?.roles)
  const isPlayer  = role === 'player'
  const accent    = 'from-emerald-950 via-emerald-900 to-green-800'

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
    <div className={`min-h-screen bg-gradient-to-br ${accent} flex flex-col`}>
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b border-white/10">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => navigate(backTarget)}
              className="text-white/50 hover:text-white transition-colors text-sm"
            >
              ← {isPlayer ? 'Home' : 'Players'}
            </button>
            <h1 className="text-lg font-bold text-white truncate">
              {isPlayer ? 'My Stats' : `Player · ${id.slice(0, 8)}…`}
            </h1>
          </div>

          {/* Date range */}
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <span className="text-xs text-white/40">Period:</span>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setDate('from', e.target.value)}
              className="bg-white/10 border border-white/20 rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:ring-2 focus:ring-white/30"
            />
            <span className="text-xs text-white/40">–</span>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setDate('to', e.target.value)}
              className="bg-white/10 border border-white/20 rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:ring-2 focus:ring-white/30"
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

          {/* Tabs */}
          <nav className="flex gap-1 overflow-x-auto">
            {TABS.map((t) => (
              <NavLink
                key={t.path}
                to={`/players/${id}/${t.path}?${params.toString()}`}
                className={({ isActive }) =>
                  `px-4 py-2 rounded-xl text-xs font-medium whitespace-nowrap transition-all ${
                    isActive
                      ? 'bg-white/20 text-white'
                      : 'text-white/50 hover:text-white hover:bg-white/10'
                  }`
                }
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>

      {/* Page content */}
      <div className="flex-1 px-6 py-6">
        <div className="max-w-3xl mx-auto">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
