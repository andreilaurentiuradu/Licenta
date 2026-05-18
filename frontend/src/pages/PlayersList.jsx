import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { getPlayers } from '../api/players'
import toast from 'react-hot-toast'

function pickRole(roles) {
  if (roles?.includes('admin'))  return 'admin'
  if (roles?.includes('coach'))  return 'coach'
  if (roles?.includes('player')) return 'player'
  return 'player'
}

export default function PlayersList() {
  const { user }    = useAuth()
  const navigate    = useNavigate()
  const role        = pickRole(user?.roles)
  const isPlayer    = role === 'player'
  const [players, setPlayers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isPlayer) {
      navigate(`/players/${user.sub}/biometrics`, { replace: true })
      return
    }
    getPlayers()
      .then((r) => setPlayers(r.data))
      .catch(() => toast.error('Failed to load players'))
      .finally(() => setLoading(false))
  }, [isPlayer, user, navigate])

  if (isPlayer) return null

  const sport   = localStorage.getItem('selected_sport') || 'football'
  const accent  = sport === 'marathon' ? 'from-orange-950 via-orange-900 to-red-800' : 'from-emerald-950 via-emerald-900 to-green-800'

  return (
    <div className={`min-h-screen bg-gradient-to-br ${accent} p-6`}>
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => navigate('/home')}
            className="text-white/50 hover:text-white transition-colors text-sm"
          >
            ← Home
          </button>
          <h1 className="text-2xl font-bold text-white">Players</h1>
        </div>

        {loading ? (
          <p className="text-white/40 text-sm">Loading…</p>
        ) : players.length === 0 ? (
          <div className="p-6 rounded-2xl bg-white/10 border border-white/15 text-white/40 text-sm text-center">
            No players found. Players need to register with the "player" role first.
          </div>
        ) : (
          <div className="space-y-3">
            {players.map((p) => (
              <button
                key={p.user_id}
                onClick={() => navigate(`/players/${p.user_id}/biometrics`)}
                className="w-full text-left p-4 rounded-2xl bg-white/10 border border-white/15 hover:bg-white/15 transition-all"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-white">{p.username}</p>
                    <p className="text-xs text-white/40 mt-0.5">{p.email}</p>
                    {p.profile && (
                      <p className="text-xs text-white/30 mt-0.5">
                        {[p.profile.position, p.profile.height_cm && `${p.profile.height_cm} cm`, p.profile.weight_kg && `${p.profile.weight_kg} kg`]
                          .filter(Boolean).join(' · ')}
                      </p>
                    )}
                  </div>
                  <span className="text-white/30 text-lg">→</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
