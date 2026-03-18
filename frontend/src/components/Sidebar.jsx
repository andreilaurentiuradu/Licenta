import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Users, TrendingUp, Network, BarChart2, Activity,
} from 'lucide-react'

const links = [
  { to: '/dashboard',   label: 'Dashboard',   icon: LayoutDashboard },
  { to: '/players',     label: 'Players',     icon: Users },
  { to: '/predictions', label: 'Predictions', icon: TrendingUp },
  { to: '/federation',  label: 'Federation',  icon: Network },
  { to: '/analytics',   label: 'Analytics',   icon: BarChart2 },
]

export default function Sidebar() {
  return (
    <aside className="w-60 bg-slate-900 text-slate-100 flex flex-col shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-6 py-5 border-b border-slate-700">
        <Activity size={22} className="text-blue-400" />
        <span className="font-bold text-lg tracking-tight">SportAnalytics</span>
      </div>

      {/* Nav links */}
      <nav className="flex-1 py-4 px-3 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-slate-700 text-xs text-slate-500">
        Privacy-by-Design · FL v2.0
      </div>
    </aside>
  )
}
