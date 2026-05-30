import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const THEMES = {
  football: { bg: 'from-emerald-950 via-emerald-900 to-green-800', accent: '#34d399', ring: 'focus:ring-emerald-500' },
  marathon: { bg: 'from-orange-950 via-orange-900 to-red-800',     accent: '#fb923c', ring: 'focus:ring-orange-500' },
}

const FAQS = [
  {
    q: 'What is LawrAnalyzer?',
    a: 'LawrAnalyzer is a platform for sports clubs that centralises player metrics — biometrics, training load, physical assessments, injury history, nutrition, sleep and stress — and uses Federated Learning and AI to help coaches prevent injuries and optimise performance.',
  },
  {
    q: 'What roles are available?',
    a: [
      'Player — views and logs only their own metrics and AI recommendations.',
      'Coach — views and manages all players in their club, triggers Federated Learning training rounds.',
      'Admin — full platform access including user creation across all clubs.',
    ],
  },
  {
    q: 'How do I record player data?',
    a: 'Navigate to a player profile and select the relevant tab: Training, Physical, Injuries or Wellness. Use the "+ Add entry" button and fill in the form. All data is filterable by date range.',
  },
  {
    q: 'Can a player see another player\'s data?',
    a: 'No. A player can only access their own metrics. Coaches and admins can view all players in their club. Access is enforced at the API level on every request.',
  },
  {
    q: 'What is Federated Learning and how does it protect my data?',
    a: 'Raw player data never leaves your club\'s infrastructure. Only model weights (not raw data) are shared with the central server for aggregation using FedAvg. Each club\'s data is never visible to other clubs.',
  },
  {
    q: 'How does injury risk prediction work?',
    a: 'The FL model uses 12 features extracted DB — position, injury history, physical assessments, sleep, stress, nutrition and warmup adherence — to compute a risk score (low / medium / high) for each player. The global model is bootstrapped from a football dataset and continuously fine-tuned as new data is logged.',
  },
  {
    q: 'How do AI recommendations work?',
    a: 'The platform collects the last 30 days of wellness, training and physical data for a player and sends it to an LLM (Groq — llama-3.1-8b-instant). The model returns 3-4 personalised, prioritised recommendations across categories: Injury Prevention, Training Load, Wellness, Nutrition and Recovery.',
  },
  {
    q: 'What metrics does the Wellness tab track?',
    a: [
      'Calories, protein, carbohydrates, fat (macros)',
      'Hydration (ml)',
      'Sleep hours and sleep quality (1-10)',
      'Stress level and mood score (1-10)',
    ],
  },
  {
    q: 'What does the Physical tab measure?',
    a: [
      'Knee strength score',
      'Hamstring flexibility',
      'Reaction time (ms)',
      'Balance test score',
      'Sprint speed over 10m (m/s)',
      'Agility score',
    ],
  },
]

const DOTS = [
  { top: '6%',  left: '4%',  delay: '0s',   size: 5 },
  { top: '22%', left: '92%', delay: '0.9s', size: 6 },
  { top: '55%', left: '2%',  delay: '1.2s', size: 4 },
  { top: '78%', left: '90%', delay: '0.4s', size: 7 },
  { top: '90%', left: '18%', delay: '1.5s', size: 4 },
]

export default function Support() {
  const navigate   = useNavigate()
  const sport      = localStorage.getItem('selected_sport') || 'football'
  const theme      = THEMES[sport] || THEMES.football
  const [open, setOpen] = useState(null)

  return (
    <>
      <style>{`
        @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }
        @keyframes slideUp { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        .dot-float { animation: float 4s ease-in-out infinite; }
        .slide-up   { animation: slideUp 0.5s ease both; }
        .slide-up-2 { animation: slideUp 0.5s ease 0.1s both; }
        .faq-item { transition: background 0.2s ease; }
        .faq-item:hover { background: rgba(255,255,255,0.12); }
      `}</style>

      <div className={`min-h-screen bg-gradient-to-br ${theme.bg} p-6 relative overflow-hidden`}>

        {/* Grid lines */}
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

          {/* Header */}
          <div className="slide-up flex items-center gap-4 mb-10">
            <button onClick={() => navigate('/home')} className="text-white/40 hover:text-white/80 transition-colors text-sm">
              ← Back
            </button>
            <div>
              <h1 className="text-2xl font-bold text-white">Support</h1>
              <p className="text-xs text-white/40 mt-0.5">Documentation & help</p>
            </div>
          </div>

          {/* Contact cards */}
          <div className="slide-up grid grid-cols-2 gap-3 mb-8">
            {[
              { icon: '📧', label: 'Email', value: 'support@lawranalyzer.io' },
              { icon: '📖', label: 'Docs', value: 'docs.lawranalyzer.io' },
            ].map((c) => (
              <div key={c.label} className="p-4 rounded-2xl bg-white/10 border border-white/15">
                <span className="text-xl block mb-2">{c.icon}</span>
                <p className="text-xs text-white/40">{c.label}</p>
                <p className="text-xs font-medium text-white mt-0.5">{c.value}</p>
              </div>
            ))}
          </div>

          {/* FAQ */}
          <div className="slide-up-2">
            <p className="text-xs font-semibold text-white/40 uppercase tracking-widest mb-4">
              Frequently Asked Questions
            </p>
            <div className="space-y-2">
              {FAQS.map((faq, i) => (
                <div
                  key={i}
                  className="faq-item rounded-2xl bg-white/8 border border-white/10 overflow-hidden cursor-pointer"
                  onClick={() => setOpen(open === i ? null : i)}
                >
                  <div className="flex items-center justify-between px-5 py-4">
                    <p className="text-sm font-medium text-white">{faq.q}</p>
                    <span className="text-white/40 text-lg ml-4 shrink-0"
                      style={{ transform: open === i ? 'rotate(45deg)' : 'none', transition: 'transform 0.2s' }}>
                      +
                    </span>
                  </div>
                  <div style={{
                    maxHeight: open === i ? '200px' : '0',
                    overflow: 'hidden',
                    transition: 'max-height 0.3s ease',
                  }}>
                    {Array.isArray(faq.a) ? (
                      <ul className="px-5 pb-4 space-y-1.5">
                        {faq.a.map((item, j) => (
                          <li key={j} className="flex items-start gap-2 text-sm text-white/50 leading-relaxed">
                            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-white/30 shrink-0" />
                            {item}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="px-5 pb-4 text-sm text-white/50 leading-relaxed">{faq.a}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
