import { useEffect, useState } from 'react'
import { useNavigate }        from 'react-router-dom'
import { useAuth }            from '../contexts/AuthContext'
import { getPlayers }         from '../api/players'
import { triggerFLRound, getFlStatus } from '../api/fl'
import toast                  from 'react-hot-toast'

function pickRole(roles) {
  if (roles?.includes('admin'))  return 'admin'
  if (roles?.includes('coach'))  return 'coach'
  if (roles?.includes('player')) return 'player'
  return 'player'
}

// ── FL Training Panel (coach only) ────────────────────────────────

function FLPanel({ club }) {
  const [flStatus, setFlStatus] = useState(null)
  const [result,   setResult]   = useState(null)
  const [loading,  setLoading]  = useState(false)

  useEffect(() => {
    getFlStatus().then(r => setFlStatus(r.data)).catch(() => {})
  }, [])

  const handleTrain = async () => {
    setLoading(true)
    setResult(null)
    try {
      const { data } = await triggerFLRound()
      setResult(data)
      if (data.warning) toast(data.warning, { icon: '⚠️', duration: 6000 })
      else toast.success('FL training round completed')
      getFlStatus().then(r => setFlStatus(r.data)).catch(() => {})
    } catch {
      toast.error('Failed to trigger FL training round')
    } finally {
      setLoading(false)
    }
  }

  const acc   = flStatus?.accuracy ?? null
  const round = flStatus?.round    ?? null

  return (
    <div className="p-5 rounded-2xl bg-white/8 border border-white/10 mb-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-sm font-semibold text-white">Federated Learning</p>
          <p className="text-xs text-white/40 mt-0.5">
            Train the global injury-prediction model using {club ? `${club}'s` : "your club's"} data.
            Raw player data never leaves the club.
          </p>
        </div>
        <button
          onClick={handleTrain}
          disabled={loading}
          className="shrink-0 px-4 py-2 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white text-xs font-semibold transition-all disabled:opacity-50"
        >
          {loading ? 'Training…' : 'Start training round →'}
        </button>
      </div>

      {/* Global model stats */}
      {flStatus?.ready && (
        <div className="mt-4 grid grid-cols-3 gap-2 text-center">
          <div className="p-2 rounded-lg bg-white/5">
            <p className="text-lg font-bold text-indigo-300">
              {acc !== null ? `${(acc * 100).toFixed(1)}%` : '—'}
            </p>
            <p className="text-xs text-white/40">Accuracy</p>
          </div>
          <div className="p-2 rounded-lg bg-white/5">
            <p className="text-lg font-bold text-white">{round ?? '—'}</p>
            <p className="text-xs text-white/40">Round</p>
          </div>
          <div className="p-2 rounded-lg bg-white/5">
            <p className="text-lg font-bold text-white">{flStatus.clubs_count ?? 0}</p>
            <p className="text-xs text-white/40">Clubs</p>
          </div>
        </div>
      )}

      {/* Training result warnings */}
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
              Round {result.fl_round} complete · {result.players_in_round} players · weights aggregated via FedAvg
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Player card ────────────────────────────────────────────────────

function PlayerCard({ p, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-2xl bg-white/10 border border-white/15 hover:bg-white/15 transition-all"
    >
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-white truncate">{p.username}</p>
            {p.club && (
              <span className="shrink-0 text-xs px-2 py-0.5 rounded-full bg-white/10 text-white/50">
                {p.club}
              </span>
            )}
          </div>
          <p className="text-xs text-white/40 mt-0.5 truncate">{p.email}</p>
          {p.profile && (
            <p className="text-xs text-white/30 mt-0.5">
              {[p.profile.position,
                p.profile.height_cm && `${p.profile.height_cm} cm`,
                p.profile.weight_kg && `${p.profile.weight_kg} kg`]
                .filter(Boolean).join(' · ')}
            </p>
          )}
        </div>
        <span className="shrink-0 text-white/30 text-lg ml-3">→</span>
      </div>
    </button>
  )
}

// ── Main component ─────────────────────────────────────────────────

export default function PlayersList() {
  const { user }    = useAuth()
  const navigate    = useNavigate()
  const role        = pickRole(user?.roles)
  const isPlayer    = role === 'player'
  const isAdmin     = role === 'admin'
  const isCoach     = role === 'coach'
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

  const sport  = localStorage.getItem('selected_sport') || 'football'
  const accent = sport === 'marathon'
    ? 'from-orange-950 via-orange-900 to-red-800'
    : 'from-emerald-950 via-emerald-900 to-green-800'

  // Admin: group by club
  const clubMap = {}
  if (isAdmin) {
    for (const p of players) {
      const key = p.club || 'No club'
      if (!clubMap[key]) clubMap[key] = []
      clubMap[key].push(p)
    }
  }

  const coachClub = user?.club

  return (
    <div className={`min-h-screen bg-gradient-to-br ${accent} p-6`}>
      <div className="max-w-2xl mx-auto">

        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => navigate('/home')}
            className="text-white/50 hover:text-white transition-colors text-sm"
          >
            ← Home
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white">
              {isAdmin ? 'All Clubs' : coachClub || 'Players'}
            </h1>
            {isCoach && coachClub && (
              <p className="text-xs text-white/40 mt-0.5">
                Showing players from {coachClub}
              </p>
            )}
          </div>
        </div>

        {/* FL panel — coach only */}
        {isCoach && <FLPanel club={coachClub} />}

        {loading ? (
          <p className="text-white/40 text-sm">Loading…</p>
        ) : players.length === 0 ? (
          <div className="p-6 rounded-2xl bg-white/10 border border-white/15 text-white/40 text-sm text-center">
            {isCoach
              ? `No players found for ${coachClub || 'your club'}. Make sure players are assigned the correct club.`
              : 'No players found. Players need to register with the "player" role first.'}
          </div>
        ) : isAdmin ? (
          // Admin: grouped by club
          <div className="space-y-6">
            {Object.entries(clubMap).sort(([a], [b]) => a.localeCompare(b)).map(([club, clubPlayers]) => (
              <div key={club}>
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-xs font-semibold text-white/60 uppercase tracking-wider">
                    {club}
                  </span>
                  <span className="text-xs text-white/30">{clubPlayers.length} player{clubPlayers.length !== 1 ? 's' : ''}</span>
                  <div className="flex-1 h-px bg-white/10" />
                </div>
                <div className="space-y-2">
                  {clubPlayers.map((p) => (
                    <PlayerCard
                      key={p.user_id}
                      p={p}
                      onClick={() => navigate(`/players/${p.user_id}/biometrics`)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          // Coach: flat list (already filtered by backend)
          <div className="space-y-3">
            {players.map((p) => (
              <PlayerCard
                key={p.user_id}
                p={p}
                onClick={() => navigate(`/players/${p.user_id}/biometrics`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
