/**
 * Decorative, theme-specific background for the player-data pages.
 *
 * Renders a handful of faint, slowly floating line-icons whose motif matches
 * the data on screen — a heartbeat & cross for Physical (health), dumbbells &
 * a flame for Training (strength), apples / leaves / a moon for Wellness
 * (nutrition + relaxation), and so on. Purely cosmetic and non-interactive.
 */

// Lucide-style 24×24 icon bodies (stroke-based, inherit currentColor).
const HEART    = '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>'
const PULSE    = '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>'
const CROSS    = '<path d="M12 5v14M5 12h14"/>'
const DUMBBELL = '<path d="M6.5 6.5 17.5 17.5"/><path d="M21 21l-1-1"/><path d="M3 3l1 1"/><path d="M18 22l4-4"/><path d="M2 6l4-4"/><path d="M3 10l7-7"/><path d="M14 21l7-7"/>'
const BOLT     = '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>'
const FLAME    = '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>'
const LEAF     = '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6"/>'
const MOON     = '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>'
const APPLE    = '<path d="M12 20.94c1.5 0 2.75 1.06 4 1.06 3 0 6-8 6-12.22A4.91 4.91 0 0 0 17 5c-2.22 0-4 1.44-5 2-1-.56-2.78-2-5-2a4.9 4.9 0 0 0-5 4.78C2 14 5 22 8 22c1.25 0 2.5-1.06 4-1.06Z"/><path d="M10 2c1 .5 2 2 2 5"/>'
const DROPLET  = '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/>'
const SHIELD   = '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
const CROSS_SQ = '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M12 8v8M8 12h8"/>'
const USER     = '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'
const GAUGE    = '<path d="M12 14 8 10"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>'
const BULB     = '<path d="M9 18h6"/><path d="M10 22h4"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/>'

// One icon set per page motif.
const VARIANTS = {
  health:   [HEART, PULSE, CROSS],                 // Physical
  strength: [DUMBBELL, FLAME, BOLT],               // Training
  wellness: [LEAF, MOON, APPLE, DROPLET],          // Wellness (nutrition + relaxation)
  medical:  [CROSS_SQ, SHIELD, PULSE],             // Injuries
  body:     [USER, GAUGE, PULSE],                  // Biometrics
  spark:    [BULB, BOLT],                          // Recommendations / default
}

// Fixed placement slots so the layout is stable between renders.
const SLOTS = [
  { top: '7%',  left: '5%',  size: 34, dur: 7.0,  delay: 0.0 },
  { top: '15%', left: '89%', size: 44, dur: 9.0,  delay: 1.2 },
  { top: '41%', left: '3%',  size: 28, dur: 8.0,  delay: 0.6 },
  { top: '58%', left: '94%', size: 36, dur: 10.0, delay: 1.8 },
  { top: '80%', left: '10%', size: 30, dur: 7.5,  delay: 0.9 },
  { top: '86%', left: '80%', size: 40, dur: 9.5,  delay: 2.1 },
  { top: '33%', left: '49%', size: 24, dur: 11.0, delay: 1.5 },
]

export default function ThemedBackground({ variant = 'health' }) {
  const icons = VARIANTS[variant] || VARIANTS.health

  return (
    <div
      data-testid="themed-bg"
      data-variant={variant}
      aria-hidden="true"
      className="absolute inset-0 z-0 overflow-hidden pointer-events-none select-none"
    >
      <style>{`
        @keyframes tb-float {
          0%, 100% { transform: translateY(0) rotate(0deg); }
          50%      { transform: translateY(-16px) rotate(6deg); }
        }
      `}</style>

      {/* Large corner watermark */}
      <svg
        viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1"
        strokeLinecap="round" strokeLinejoin="round"
        className="absolute -bottom-10 -right-8 text-white"
        style={{ width: 260, height: 260, opacity: 0.04 }}
        dangerouslySetInnerHTML={{ __html: icons[0] }}
      />

      {/* Floating glyphs */}
      {SLOTS.map((s, i) => (
        <svg
          key={i}
          viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"
          className="absolute text-white"
          style={{
            top: s.top, left: s.left, width: s.size, height: s.size,
            opacity: 0.1,
            animation: `tb-float ${s.dur}s ease-in-out ${s.delay}s infinite`,
          }}
          dangerouslySetInnerHTML={{ __html: icons[i % icons.length] }}
        />
      ))}
    </div>
  )
}
