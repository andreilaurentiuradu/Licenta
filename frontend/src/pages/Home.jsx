import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function Home() {
  const { user, logout } = useAuth()
  const navigate         = useNavigate()
  const isAdmin          = user?.roles?.includes('admin')

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 w-full max-w-sm p-8 text-center">

        {/* Role badge */}
        <span className={`inline-block text-xs font-semibold px-3 py-1 rounded-full mb-6 ${
          isAdmin
            ? 'bg-purple-100 text-purple-700'
            : 'bg-blue-100 text-blue-700'
        }`}>
          {isAdmin ? 'Admin' : 'Coach'}
        </span>

        <h1 className="text-2xl font-semibold text-slate-800">
          Welcome, {user?.username}!
        </h1>
        <p className="text-slate-400 text-sm mt-2">SportAnalytics Platform</p>

        <div className="mt-6 p-4 bg-slate-50 rounded-xl text-sm text-slate-500">
          {isAdmin
            ? 'You have administrator access. More features coming in Sprint 2.'
            : 'You are logged in as a coach. Player analytics coming in Sprint 2.'}
        </div>

        <button
          onClick={handleLogout}
          className="mt-6 text-xs text-slate-400 hover:text-slate-600 transition-colors"
        >
          Sign out
        </button>
      </div>
    </div>
  )
}
