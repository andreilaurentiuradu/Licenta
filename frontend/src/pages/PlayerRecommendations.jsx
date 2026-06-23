import { useEffect, useRef, useState } from 'react'
import { useParams }           from 'react-router-dom'
import {
  getRecommendations,
  acceptRecommendation, refuseRecommendation, completeRecommendation,
} from '../api/players'
import toast from 'react-hot-toast'

const POLL_MS = 15000   // light polling so a second device stays roughly in sync

const PRIORITY_STYLE = {
  high:   { badge: 'bg-red-500/20 text-red-300',         dot: 'bg-red-400'     },
  medium: { badge: 'bg-amber-500/20 text-amber-300',     dot: 'bg-amber-400'   },
  low:    { badge: 'bg-emerald-500/20 text-emerald-300', dot: 'bg-emerald-400' },
}

const RISK_META = {
  low:    { bar: 'bg-emerald-400', width: '25%', label: 'Low risk',    text: 'text-emerald-300' },
  medium: { bar: 'bg-amber-400',   width: '60%', label: 'Medium risk', text: 'text-amber-300'   },
  high:   { bar: 'bg-red-400',     width: '90%', label: 'High risk',   text: 'text-red-300'     },
}

export default function PlayerRecommendations() {
  const { id }              = useParams()
  const [data, setData]     = useState(null)
  const [loading, setLoading]   = useState(true)
  const [busyId, setBusyId]     = useState(null)

  // Latest "action in flight" flag, readable from the polling interval without
  // re-subscribing it on every render.
  const busyRef = useRef(false)
  busyRef.current = busyId !== null

  // Silent background refresh — never toggles the loading spinner.
  const refresh = () =>
    getRecommendations(id).then((r) => setData(r.data)).catch(() => {})

  // Initial load (with spinner).
  useEffect(() => {
    getRecommendations(id)
      .then((r) => setData(r.data))
      .catch(() => toast.error('Failed to load recommendations'))
      .finally(() => setLoading(false))
  }, [id])

  // Light polling: refresh on an interval, plus whenever the tab regains focus.
  // Skips a tick while the tab is hidden or an action is in flight, so it never
  // clobbers an optimistic update mid-action.
  useEffect(() => {
    const tick = () => {
      if (document.visibilityState !== 'visible' || busyRef.current) return
      refresh()
    }
    const interval  = setInterval(tick, POLL_MS)
    const onVisible = () => { if (document.visibilityState === 'visible') tick() }
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('focus', onVisible)
    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('focus', onVisible)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // A 409 means another device already acted on this recommendation; the
  // server returns the fresh state so we resync instead of failing.
  const handleConflict = (err) => {
    if (err.response?.status === 409) {
      setData(err.response.data)
      toast('Recommendations were updated on another device.', { icon: '🔄' })
      return true
    }
    return false
  }

  const accept = async (rid) => {
    setBusyId(rid)
    try {
      const { data: rec } = await acceptRecommendation(id, rid)
      setData((d) => ({
        ...d,
        active: d.active.map((r) => (r.id === rid ? rec : r)),
      }))
    } catch (err) {
      if (!handleConflict(err)) toast.error('Action failed')
    } finally { setBusyId(null) }
  }

  // Both refuse and complete move the item to history and add a fresh
  // same-category replacement to the active list.
  const moveToHistory = async (rid, apiCall, successMsg) => {
    setBusyId(rid)
    try {
      const { data: res } = await apiCall(id, rid)
      setData((d) => ({
        ...d,
        active:  [...d.active.filter((r) => r.id !== rid), res.replacement],
        history: [res.item, ...d.history],
      }))
      toast.success(successMsg)
    } catch (err) {
      if (!handleConflict(err)) toast.error('Action failed')
    } finally { setBusyId(null) }
  }

  const refuse   = (rid) => moveToHistory(rid, refuseRecommendation,   'Replaced with another recommendation')
  const complete = (rid) => moveToHistory(rid, completeRecommendation, 'Completed — added a new one')

  if (loading) return (
    <div className="flex items-center gap-3 text-white/40 text-sm py-6">
      <svg className="animate-spin h-4 w-4 text-indigo-400" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
      </svg>
      Loading recommendations…
    </div>
  )
  if (!data) return null

  const risk = RISK_META[data.injury_risk] || RISK_META.low

  return (
    <div className="space-y-4">

      {/* Injury risk bar */}
      <div className="p-5 rounded-2xl bg-white/10 border border-white/15">
        <p className="text-xs text-white/50 mb-3 uppercase tracking-wider">Injury Risk</p>
        <div className="flex items-center gap-4">
          <div className="flex-1 h-2 rounded-full bg-white/10 overflow-hidden">
            <div className={`h-full rounded-full transition-all duration-700 ${risk.bar}`} style={{ width: risk.width }} />
          </div>
          <span className={`text-sm font-semibold shrink-0 ${risk.text}`}>{risk.label}</span>
        </div>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-white/40">
          {data.ai_enabled ? '✦ AI-generated recommendations' : '○ Default recommendations'}
        </p>
        <p className="text-xs text-white/30">Complete or refuse one to get a new one of the same type</p>
      </div>

      {/* Active recommendations */}
      {data.active.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {data.active.map((rec) => {
            const s = PRIORITY_STYLE[rec.priority] || PRIORITY_STYLE.low
            const isAccepted = rec.status === 'accepted'
            const busy = busyId === rec.id
            return (
              <div key={rec.id} className="p-5 rounded-2xl bg-white/10 border border-white/15 flex flex-col">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`w-2 h-2 rounded-full shrink-0 ${s.dot}`} />
                  <p className="text-sm font-semibold text-white">{rec.category}</p>
                  {isAccepted && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 shrink-0">✓ Accepted</span>
                  )}
                  <span className={`ml-auto text-xs px-2 py-0.5 rounded-full shrink-0 ${s.badge}`}>{rec.priority}</span>
                </div>
                <p className="text-sm text-white/70 leading-relaxed flex-1">{rec.text}</p>

                <div className="flex flex-wrap gap-2 mt-4">
                  {!isAccepted && (
                    <button onClick={() => accept(rec.id)} disabled={busy}
                      className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 text-xs font-medium hover:bg-emerald-500/30 transition-all disabled:opacity-50">
                      ✓ Accept
                    </button>
                  )}
                  <button onClick={() => refuse(rec.id)} disabled={busy}
                    className="px-3 py-1.5 rounded-lg bg-red-500/15 text-red-300 text-xs font-medium hover:bg-red-500/25 transition-all disabled:opacity-50">
                    ✕ Refuse
                  </button>
                  <button onClick={() => complete(rec.id)} disabled={busy}
                    className="px-3 py-1.5 rounded-lg bg-white/10 text-white/70 text-xs font-medium hover:bg-white/20 transition-all disabled:opacity-50">
                    Mark complete
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <p className="text-white/30 text-sm text-center py-8">
          No active recommendations.
        </p>
      )}

      {/* History — completed & refused */}
      {data.history.length > 0 && (
        <div className="pt-2">
          <p className="text-xs font-semibold text-white/40 uppercase tracking-widest mb-3">
            History ({data.history.length})
          </p>
          <div className="space-y-2">
            {data.history.map((rec) => {
              const refused = rec.status === 'refused'
              return (
                <div key={rec.id} className="flex items-start gap-3 px-4 py-3 rounded-xl bg-white/5 border border-white/10">
                  <span className={`mt-0.5 shrink-0 ${refused ? 'text-red-400' : 'text-emerald-400'}`}>
                    {refused ? '✕' : '✓'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-white/50">
                      {rec.category}
                      <span className="ml-2 text-white/30">· {refused ? 'refused' : 'completed'}</span>
                    </p>
                    <p className="text-sm text-white/40 line-through leading-relaxed">{rec.text}</p>
                  </div>
                  {rec.updated_at && (
                    <span className="text-xs text-white/25 shrink-0">{rec.updated_at.slice(0, 10)}</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

    </div>
  )
}
