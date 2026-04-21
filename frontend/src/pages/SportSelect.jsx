import { useNavigate } from 'react-router-dom'

const SPORTS = [
  {
    key: 'football',
    label: 'Football',
    icon: '⚽',
    description: 'Injury risk prediction for football players',
  },
  {
    key: 'marathon',
    label: 'Marathon',
    icon: '🏃',
    description: 'Performance analytics for long-distance runners',
  },
]

export default function SportSelect() {
  const navigate = useNavigate()

  const handleSelect = (sport) => {
    localStorage.setItem('selected_sport', sport)
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col items-center justify-center p-6">
      <h1 className="text-2xl font-semibold text-slate-800 mb-1">SportAnalytics</h1>
      <p className="text-sm text-slate-400 mb-10">Select your sport to continue</p>

      <div className="flex flex-col sm:flex-row gap-4 w-full max-w-md">
        {SPORTS.map((sport) => (
          <button
            key={sport.key}
            onClick={() => handleSelect(sport.key)}
            className="flex-1 bg-white border-2 border-slate-200 rounded-2xl p-8 text-center hover:border-slate-400 hover:shadow-md transition-all group"
          >
            <span className="text-5xl block mb-4">{sport.icon}</span>
            <p className="text-base font-semibold text-slate-800 mb-1">{sport.label}</p>
            <p className="text-xs text-slate-400">{sport.description}</p>
          </button>
        ))}
      </div>
    </div>
  )
}
