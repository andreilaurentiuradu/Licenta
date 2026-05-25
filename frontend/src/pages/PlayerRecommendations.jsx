import { useEffect, useState } from 'react'
import { useParams }           from 'react-router-dom'
import { getRecommendations }  from '../api/players'
import toast                   from 'react-hot-toast'

const PRIORITY_STYLE = {
  high:   { badge: 'bg-red-500/20 text-red-300',    dot: 'bg-red-400'    },
  medium: { badge: 'bg-amber-500/20 text-amber-300', dot: 'bg-amber-400'  },
  low:    { badge: 'bg-emerald-500/20 text-emerald-300', dot: 'bg-emerald-400' },
}

const RISK_STYLE = {
  low:    { bar: 'bg-emerald-400', label: 'Low risk',    text: 'text-emerald-300' },
  medium: { bar: 'bg-amber-400',   label: 'Medium risk', text: 'text-amber-300'   },
  high:   { bar: 'bg-red-400',     label: 'High risk',   text: 'text-red-300'     },
}

export default function PlayerRecommendations() {
  const { id }  = useParams()
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getRecommendations(id)
      .then((r) => setData(r.data))
      .catch(() => toast.error('Failed to load recommendations'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <p className="text-white/40 text-sm">Loading…</p>
  if (!data)   return null

  const riskStyle = RISK_STYLE[data.injury_risk] || RISK_STYLE.low

  return (
    <div className="space-y-5">

      {/* Injury risk card */}
      <div className="p-5 rounded-2xl bg-white/10 border border-white/15">
        <p className="text-xs text-white/50 mb-2 uppercase tracking-wider">Injury Risk Score</p>
        <div className="flex items-center gap-4">
          <div className="flex-1 h-2 rounded-full bg-white/10 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${riskStyle.bar}`}
              style={{ width: data.injury_risk === 'low' ? '25%' : data.injury_risk === 'medium' ? '60%' : '90%' }}
            />
          </div>
          <span className={`text-sm font-semibold ${riskStyle.text}`}>{riskStyle.label}</span>
        </div>
      </div>

      {/* Recommendations */}
      <div className="space-y-3">
        {data.recommendations.map((rec, i) => {
          const style = PRIORITY_STYLE[rec.priority] || PRIORITY_STYLE.low
          return (
            <div key={i} className="p-5 rounded-2xl bg-white/10 border border-white/15">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-2 h-2 rounded-full shrink-0 ${style.dot}`} />
                <p className="text-sm font-semibold text-white">{rec.category}</p>
                <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${style.badge}`}>
                  {rec.priority}
                </span>
              </div>
              <p className="text-sm text-white/70 leading-relaxed">{rec.text}</p>
            </div>
          )
        })}
      </div>

      {/* Sprint 3 note */}
      <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/20">
        <p className="text-xs text-indigo-300/80">{data.note}</p>
      </div>

    </div>
  )
}
