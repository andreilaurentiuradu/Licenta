import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'

const THEMES = {
  football: { bg: 'from-emerald-950 via-emerald-900 to-green-800', accent: '#34d399', ring: 'focus:ring-emerald-500', btn: 'bg-emerald-500 hover:bg-emerald-400' },
  marathon: { bg: 'from-orange-950 via-orange-900 to-red-800',     accent: '#fb923c', ring: 'focus:ring-orange-500', btn: 'bg-orange-500 hover:bg-orange-400' },
}

const DOTS = [
  { top: '7%',  left: '6%',  delay: '0s',   size: 5 },
  { top: '20%', left: '90%', delay: '0.8s', size: 6 },
  { top: '52%', left: '3%',  delay: '1.3s', size: 4 },
  { top: '76%', left: '91%', delay: '0.4s', size: 7 },
  { top: '88%', left: '20%', delay: '1.1s', size: 4 },
]

const ASPECTS = ['Overall experience', 'UI & Design', 'Performance', 'Ease of use']

export default function Feedback() {
  const navigate = useNavigate()
  const sport    = localStorage.getItem('selected_sport') || 'football'
  const theme    = THEMES[sport] || THEMES.football

  const [ratings,  setRatings]  = useState({})
  const [message,  setMessage]  = useState('')
  const [hover,    setHover]    = useState({})
  const [loading,  setLoading]  = useState(false)
  const [sent,     setSent]     = useState(false)

  const setRating = (aspect, val) => setRatings((r) => ({ ...r, [aspect]: val }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (Object.keys(ratings).length < ASPECTS.length) {
      toast.error('Please rate all aspects')
      return
    }
    setLoading(true)
    await new Promise((r) => setTimeout(r, 800))
    setLoading(false)
    setSent(true)
    toast.success('Thank you for your feedback!')
  }

  return (
    <>
      <style>{`
        @keyframes float  { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }
        @keyframes slideUp{ from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        @keyframes popIn  { from{opacity:0;transform:scale(0.7)} to{opacity:1;transform:scale(1)} }
        .dot-float  { animation: float 4s ease-in-out infinite; }
        .slide-up   { animation: slideUp 0.5s ease both; }
        .slide-up-2 { animation: slideUp 0.5s ease 0.1s both; }
        .slide-up-3 { animation: slideUp 0.5s ease 0.2s both; }
        .pop-in     { animation: popIn 0.4s ease both; }
        .star-btn   { transition: transform 0.15s ease; }
        .star-btn:hover { transform: scale(1.2); }
      `}</style>

      <div className={`min-h-screen bg-gradient-to-br ${theme.bg} p-6 relative overflow-hidden`}>

        <div className="absolute inset-0 pointer-events-none">
          {['25%','50%','75%'].map(t => <div key={t} className="absolute w-full h-px bg-white opacity-5" style={{ top: t }} />)}
          {['33%','66%'].map(l => <div key={l} className="absolute h-full w-px bg-white opacity-5" style={{ left: l }} />)}
        </div>

        {DOTS.map((d, i) => (
          <div key={i} className="dot-float absolute rounded-full bg-white pointer-events-none"
            style={{ top: d.top, left: d.left, width: d.size, height: d.size, opacity: 0.12, animationDelay: d.delay }}
          />
        ))}

        <div className="relative z-10 max-w-lg mx-auto pt-4">

          <div className="slide-up flex items-center gap-4 mb-10">
            <button onClick={() => navigate('/home')} className="text-white/40 hover:text-white/80 transition-colors text-sm">
              ← Back
            </button>
            <div>
              <h1 className="text-2xl font-bold text-white">Feedback</h1>
              <p className="text-xs text-white/40 mt-0.5">Share your thoughts</p>
            </div>
          </div>

          {sent ? (
            <div className="pop-in text-center py-16">
              <div className="text-6xl mb-6">🎉</div>
              <h2 className="text-xl font-bold text-white mb-2">Thanks for your feedback!</h2>
              <p className="text-sm text-white/40 mb-8">Your input helps us improve SportAnalytics.</p>
              <button
                onClick={() => navigate('/home')}
                className={`${theme.btn} text-white text-sm font-semibold px-6 py-2.5 rounded-xl transition-all duration-200`}
              >
                Back to Home
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">

              <div className="slide-up-2">
                <p className="text-xs font-semibold text-white/40 uppercase tracking-widest mb-4">Rate your experience</p>
                <div className="space-y-3">
                  {ASPECTS.map((aspect) => (
                    <div key={aspect} className="flex items-center justify-between p-4 rounded-2xl bg-white/8 border border-white/10">
                      <p className="text-sm text-white">{aspect}</p>
                      <div className="flex gap-1">
                        {[1,2,3,4,5].map((star) => {
                          const filled = star <= (hover[aspect] ?? ratings[aspect] ?? 0)
                          return (
                            <button
                              key={star}
                              type="button"
                              className="star-btn text-xl leading-none"
                              style={{ color: filled ? theme.accent : 'rgba(255,255,255,0.2)' }}
                              onMouseEnter={() => setHover((h) => ({ ...h, [aspect]: star }))}
                              onMouseLeave={() => setHover((h) => ({ ...h, [aspect]: 0 }))}
                              onClick={() => setRating(aspect, star)}
                            >
                              ★
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="slide-up-3">
                <p className="text-xs font-semibold text-white/40 uppercase tracking-widest mb-4">Additional comments</p>
                <textarea
                  className={`w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:ring-2 ${theme.ring} focus:border-transparent transition-all resize-none`}
                  rows={4}
                  placeholder="Tell us what you think, what could be improved, or what you love about the platform…"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                />
              </div>

              <div className="slide-up-3">
                <button
                  type="submit"
                  disabled={loading}
                  className={`w-full ${theme.btn} text-white text-sm font-semibold py-2.5 rounded-xl transition-all duration-200 disabled:opacity-50`}
                >
                  {loading ? 'Sending…' : 'Submit feedback →'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </>
  )
}
