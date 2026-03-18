import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { LogOut, Shield } from 'lucide-react'

export default function Header() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Shield size={16} className="text-green-500" />
        <span>GDPR Compliant · Federated Learning</span>
      </div>
      <div className="flex items-center gap-3">
        {user && (
          <>
            <div className="text-sm text-right">
              <p className="font-medium text-slate-800">{user.username}</p>
              <p className="text-slate-400 text-xs capitalize">{user.role} · {user.team_name}</p>
            </div>
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold">
              {user.username[0].toUpperCase()}
            </div>
            <button onClick={handleLogout} className="p-2 text-slate-400 hover:text-red-500 transition-colors">
              <LogOut size={18} />
            </button>
          </>
        )}
      </div>
    </header>
  )
}
