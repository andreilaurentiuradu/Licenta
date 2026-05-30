import { useEffect, useState } from 'react'
import { useParams }           from 'react-router-dom'
import { getRecommendations }  from '../api/players'
import toast                   from 'react-hot-toast'

const PRIORITY_STYLE = {
  high:   { badge: 'bg-red-500/20 text-red-300',         dot: 'bg-red-400'         },
  medium: { badge: 'bg-amber-500/20 text-amber-300',     dot: 'bg-amber-400'       },
  low:    { badge: 'bg-emerald-500/20 text-emerald-300', dot: 'bg-emerald-400'     },
}

const RISK_META = {
  low:    { bar: 'bg-emerald-400', width: '25%', label: 'Low risk',    text: 'text-emerald-300' },
  medium: { bar: 'bg-amber-400',   width: '60%', label: 'Medium risk', text: 'text-amber-300'   },
  high:   { bar: 'bg-red-400',     width: '90%', label: 'High risk',   text: 'text-red-300'     },
}

export default function PlayerRecommendations() {
  const { id }                    = useParams()
  const [data,    setData]        = useState(null)
  const [loading, setLoading]     = useState(true)

  useEffect(() => {
    getRecommendations(id)
      .then((r) => setData(r.data))
      .catch(() => toast.error('Failed to load recommendations'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return (
    <div className="flex items-center gap-3 text-white/40 text-sm py-6">
      <svg className="animate-spin h-4 w-4 text-indigo-400" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
      </svg>
      Generating recommendations…
    </div>
  )
  if (!data) return null

  const risk = RISK_META[data.injury_risk] || RISK_META.low

  return (
    <div className="space-y-4">

      {/* AI / fallback badge */}
      <div className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-xs ${
        data.ai_generated
          ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-300'
          : 'bg-white/5 border-white/10 text-white/40'
      }`}>
        <span>{data.ai_generated ? '✦ AI-generated' : '○ Default'}</span>
        <span className="opacity-60">{data.note}</span>
      </div>

      {/* Injury risk bar */}
      <div className="p-5 rounded-2xl bg-white/10 border border-white/15">
        <p className="text-xs text-white/50 mb-3 uppercase tracking-wider">Injury Risk</p>
        <div className="flex items-center gap-4">
          <div className="flex-1 h-2 rounded-full bg-white/10 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${risk.bar}`}
              style={{ width: risk.width }}
            />
          </div>
          <span className={`text-sm font-semibold shrink-0 ${risk.text}`}>{risk.label}</span>
        </div>
      </div>

      {/* Recommendation cards — 1 col mobile, 2 col desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {(data.recommendations ?? []).map((rec, i) => {
          const s = PRIORITY_STYLE[rec.priority] || PRIORITY_STYLE.low
          return (
            <div key={i} className="p-5 rounded-2xl bg-white/10 border border-white/15">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-2 h-2 rounded-full shrink-0 ${s.dot}`} />
                <p className="text-sm font-semibold text-white">{rec.category}</p>
                <span className={`ml-auto text-xs px-2 py-0.5 rounded-full shrink-0 ${s.badge}`}>
                  {rec.priority}
                </span>
              </div>
              <p className="text-sm text-white/70 leading-relaxed">{rec.text}</p>
            </div>
          )
        })}
      </div>

    </div>
  )
}
