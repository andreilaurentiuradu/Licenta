import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { listFeedback } from '../api/auth'

const BG = 'from-emerald-950 via-emerald-900 to-green-800'

const STAR_ASPECTS = [
  'Overall experience',
  'Performance analytics',
  'Injury risk insights',
  'Ease of use',
]

const DOTS = [
  { top: '7%',  left: '5%',  delay: '0s',   size: 5 },
  { top: '22%', left: '91%', delay: '0.8s', size: 6 },
  { top: '55%', left: '3%',  delay: '1.2s', size: 4 },
  { top: '78%', left: '90%', delay: '0.4s', size: 7 },
]

function Stars({ value }) {
  return (
    <span className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map(n => (
        <span key={n} className={n <= value ? 'text-amber-400' : 'text-white/15'}>★</span>
      ))}
    </span>
  )
}

function avgRating(ratings) {
  const vals = Object.values(ratings || {}).filter(v => typeof v === 'number')
  if (!vals.length) return null
  return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1)
}

export default function AdminFeedback() {
  const navigate = useNavigate()
  const [items,   setItems]   = useState([])
  const [loading, setLoading] = useState(true)
  const [search,  setSearch]  = useState('')

  useEffect(() => {
    listFeedback()
      .then(r => setItems(r.data))
      .catch(() => toast.error('Failed to load feedback'))
      .finally(() => setLoading(false))
  }, [])

  const visible = items.filter(fb => {
    const q = search.toLowerCase()
    return !q ||
      fb.username?.toLowerCase().includes(q) ||
      fb.message?.toLowerCase().includes(q)
  })

  const overallAvg = items.length
    ? (items.map(fb => parseFloat(avgRating(fb.ratings) || 0))
        .reduce((a, b) => a + b, 0) / items.length).toFixed(1)
    : null

  const aspectAvgs = STAR_ASPECTS.map(aspect => {
    const vals = items.map(fb => fb.ratings?.[aspect]).filter(v => typeof v === 'number')
    return {
      label: aspect,
      avg: vals.length ? (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1) : null,
      count: vals.length,
    }
  })

  return (
    <>
      <style>{`
        @keyframes float  { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }
        @keyframes slideUp{ from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        .dot-float { animation: float 4s ease-in-out infinite; }
        .slide-up  { animation: slideUp 0.5s ease both; }
        .slide-up-2{ animation: slideUp 0.5s ease 0.1s both; }
      `}</style>

      <div className={`min-h-screen bg-gradient-to-br ${BG} p-4 sm:p-6 relative overflow-hidden`}>
        {DOTS.map((d, i) => (
          <div key={i} className="dot-float absolute rounded-full bg-white pointer-events-none"
            style={{ top: d.top, left: d.left, width: d.size, height: d.size, opacity: 0.12, animationDelay: d.delay }}
          />
        ))}

        <div className="relative z-10 max-w-lg lg:max-w-4xl mx-auto pt-4">

          {/* Header */}
          <div className="slide-up flex items-center gap-4 mb-8">
            <button onClick={() => navigate('/home')} className="text-white/40 hover:text-white/80 transition-colors text-sm shrink-0">
              ← Back
            </button>
            <div>
              <h1 className="text-2xl font-bold text-white">User Feedback</h1>
              <p className="text-xs text-white/40 mt-0.5">{items.length} submission{items.length !== 1 ? 's' : ''} from players and coaches</p>
            </div>
          </div>

          {/* Summary stats */}
          {!loading && items.length > 0 && (
            <div className="slide-up mb-6 p-5 rounded-2xl bg-white/8 border border-white/10">
              <div className="flex items-center gap-3 mb-4">
                <p className="text-sm font-semibold text-white">Overall average</p>
                <span className="text-2xl font-bold text-amber-400">{overallAvg}</span>
                <Stars value={Math.round(parseFloat(overallAvg))} />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {aspectAvgs.map(a => (
                  <div key={a.label} className="p-3 rounded-xl bg-white/5">
                    <p className="text-xs text-white/40 mb-1 truncate">{a.label}</p>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-white">{a.avg ?? '—'}</span>
                      {a.avg && <Stars value={Math.round(parseFloat(a.avg))} />}
                    </div>
                    <p className="text-xs text-white/30 mt-0.5">{a.count} rating{a.count !== 1 ? 's' : ''}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Search */}
          {!loading && items.length > 0 && (
            <div className="slide-up-2 mb-4">
              <input
                type="text"
                placeholder="Search by username or message…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-2 text-sm text-white placeholder-white/30 outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          )}

          {/* Submissions */}
          {loading ? (
            <p className="text-white/40 text-sm">Loading…</p>
          ) : visible.length === 0 ? (
            <p className="text-white/30 text-sm text-center py-10">
              {items.length === 0 ? 'No feedback submitted yet.' : 'No results match your search.'}
            </p>
          ) : (
            <div className="slide-up-2 space-y-3">
              {visible.map((fb, i) => (
                <div key={fb.id ?? i} className="p-4 rounded-2xl bg-white/8 border border-white/10">
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                        <span className="text-xs font-bold text-white/70">
                          {(fb.username || '?')[0].toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-white">{fb.username || 'Anonymous'}</p>
                        {fb.created_at && (
                          <p className="text-xs text-white/30">
                            {new Date(fb.created_at).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    </div>
                    <span className="text-lg font-bold text-amber-400 shrink-0">
                      {avgRating(fb.ratings) ?? '—'}
                    </span>
                  </div>

                  {/* Ratings per aspect */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 mb-3">
                    {Object.entries(fb.ratings || {}).map(([aspect, val]) => (
                      <div key={aspect} className="flex items-center justify-between gap-2 px-3 py-1.5 rounded-lg bg-white/5">
                        <p className="text-xs text-white/50 truncate">{aspect}</p>
                        <Stars value={val} />
                      </div>
                    ))}
                  </div>

                  {/* Message */}
                  {fb.message && (
                    <p className="text-sm text-white/60 leading-relaxed italic">
                      "{fb.message}"
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
