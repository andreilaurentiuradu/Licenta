import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const SPORTS = [
  {
    key: 'football',
    label: 'Football',
    subtitle: 'Injury risk · Tactical analytics · Player performance',
    emoji: '⚽',
    bg: 'from-emerald-950 via-emerald-900 to-green-800',
    accent: 'text-emerald-400',
    border: 'border-emerald-500',
    btn: 'bg-emerald-500 hover:bg-emerald-400',
    dots: ['top-10 left-10', 'top-32 right-16', 'bottom-20 left-24', 'bottom-10 right-10', 'top-1/2 left-6'],
    lines: [
      { top: '20%', left: '0', width: '100%', opacity: 0.08 },
      { top: '50%', left: '0', width: '100%', opacity: 0.06 },
      { top: '80%', left: '0', width: '100%', opacity: 0.08 },
    ],
  },
  {
    key: 'marathon',
    label: 'Marathon',
    subtitle: 'Endurance metrics · Pace prediction · Race readiness',
    emoji: '🏃',
    bg: 'from-orange-950 via-orange-900 to-red-800',
    accent: 'text-orange-400',
    border: 'border-orange-500',
    btn: 'bg-orange-500 hover:bg-orange-400',
    dots: ['top-16 right-12', 'top-40 left-20', 'bottom-24 right-20', 'bottom-8 left-16', 'top-1/2 right-8'],
    lines: [
      { top: '15%', left: '0', width: '60%', opacity: 0.1 },
      { top: '45%', left: '20%', width: '80%', opacity: 0.07 },
      { top: '75%', left: '0', width: '70%', opacity: 0.1 },
    ],
  },
]

export default function SportSelect() {
  const navigate = useNavigate()
  const [hovered, setHovered] = useState(null)

  const handleSelect = (sport) => {
    localStorage.setItem('selected_sport', sport)
    navigate('/home')
  }

  return (
    <>
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-18px) rotate(8deg); }
        }
        @keyframes floatSlow {
          0%, 100% { transform: translateY(0px) scale(1); }
          50% { transform: translateY(-10px) scale(1.05); }
        }
        @keyframes pulse-ring {
          0% { transform: scale(0.95); opacity: 0.6; }
          100% { transform: scale(1.15); opacity: 0; }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(24px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .sport-card { transition: flex 0.5s cubic-bezier(0.4,0,0.2,1); }
        .sport-emoji { animation: floatSlow 3.5s ease-in-out infinite; }
        .dot-float { animation: float 4s ease-in-out infinite; }
        .slide-up { animation: slideUp 0.6s ease both; }
      `}</style>

      <div className="flex h-screen overflow-hidden font-sans">
        {SPORTS.map((sport, i) => {
          const isHovered = hovered === sport.key
          const otherHovered = hovered && hovered !== sport.key

          return (
            <div
              key={sport.key}
              className={`sport-card relative flex flex-col items-center justify-center cursor-pointer bg-gradient-to-b ${sport.bg} overflow-hidden`}
              style={{
                flex: isHovered ? 1.6 : otherHovered ? 0.6 : 1,
              }}
              onMouseEnter={() => setHovered(sport.key)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => handleSelect(sport.key)}
            >
              {/* Pitch / track lines */}
              {sport.lines.map((l, j) => (
                <div
                  key={j}
                  className="absolute h-px bg-white pointer-events-none"
                  style={{ top: l.top, left: l.left, width: l.width, opacity: l.opacity }}
                />
              ))}

              {/* Floating dots */}
              {sport.dots.map((pos, j) => (
                <div
                  key={j}
                  className={`dot-float absolute w-2 h-2 rounded-full bg-white pointer-events-none`}
                  style={{
                    ...Object.fromEntries(
                      pos.split(' ').map((p) => {
                        if (p.startsWith('top-')) return ['top', p.replace('top-', '').includes('/') ? '50%' : `${parseInt(p.replace('top-', '')) * 4}px`]
                        if (p.startsWith('bottom-')) return ['bottom', `${parseInt(p.replace('bottom-', '')) * 4}px`]
                        if (p.startsWith('left-')) return ['left', p.replace('left-', '').includes('/') ? '6%' : `${parseInt(p.replace('left-', '')) * 4}px`]
                        if (p.startsWith('right-')) return ['right', p.replace('right-', '').includes('/') ? '8%' : `${parseInt(p.replace('right-', '')) * 4}px`]
                        return []
                      })
                    ),
                    opacity: 0.15,
                    animationDelay: `${j * 0.5}s`,
                  }}
                />
              ))}

              {/* Vertical divider */}
              {i === 0 && (
                <div className="absolute right-0 top-0 h-full w-px bg-white opacity-10 z-10" />
              )}

              {/* Content */}
              <div className="relative z-10 flex flex-col items-center text-center px-8 select-none">

                {/* Emoji */}
                <div className="relative mb-6">
                  {isHovered && (
                    <div
                      className="absolute inset-0 rounded-full border-2 border-white"
                      style={{ animation: 'pulse-ring 1.2s ease-out infinite' }}
                    />
                  )}
                  <span
                    className="sport-emoji block text-7xl"
                    style={{ animationDelay: `${i * 0.3}s` }}
                  >
                    {sport.emoji}
                  </span>
                </div>

                {/* Label */}
                <h2 className="text-3xl font-bold text-white mb-2 tracking-tight">
                  {sport.label}
                </h2>

                {/* Subtitle — shows on hover */}
                <p
                  className={`text-sm transition-all duration-300 ${sport.accent} max-w-48`}
                  style={{ opacity: isHovered ? 1 : 0, transform: isHovered ? 'translateY(0)' : 'translateY(6px)' }}
                >
                  {sport.subtitle}
                </p>

                {/* CTA button */}
                <button
                  className={`mt-8 px-6 py-2.5 rounded-full text-sm font-semibold text-white transition-all duration-300 ${sport.btn}`}
                  style={{
                    opacity: isHovered ? 1 : 0,
                    transform: isHovered ? 'translateY(0) scale(1)' : 'translateY(10px) scale(0.95)',
                  }}
                >
                  Get started →
                </button>
              </div>

              {/* Bottom label (visible when not hovered) */}
              <p
                className="absolute bottom-8 text-xs text-white tracking-widest uppercase transition-opacity duration-300"
                style={{ opacity: isHovered ? 0 : 0.4, letterSpacing: '0.2em' }}
              >
                {sport.label}
              </p>
            </div>
          )
        })}

        {/* Center title overlay */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-start pt-10 pointer-events-none z-20"
          style={{ opacity: hovered ? 0 : 1, transition: 'opacity 0.3s' }}
        >
          <p className="text-white text-xs tracking-widest uppercase" style={{ opacity: 0.5, letterSpacing: '0.3em' }}>
            LawrAnalyzer · Choose your sport
          </p>
        </div>
      </div>
    </>
  )
}
