import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import SportSelect      from './pages/SportSelect'
import Login            from './pages/Login'
import Register         from './pages/Register'
import Home             from './pages/Home'
import Support          from './pages/Support'
import Feedback         from './pages/Feedback'
import Profile          from './pages/Profile'
import UserManagement   from './pages/UserManagement'
import PlayersList      from './pages/PlayersList'
import PlayerLayout     from './pages/PlayerLayout'
import PlayerBiometrics from './pages/PlayerBiometrics'
import PlayerTraining   from './pages/PlayerTraining'
import PlayerPhysical   from './pages/PlayerPhysical'
import PlayerInjuries   from './pages/PlayerInjuries'
import PlayerWellness   from './pages/PlayerWellness'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen text-slate-400 text-sm">Loading…</div>
  return user ? children : <Navigate to="/login" replace />
}

function AdminRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen text-slate-400 text-sm">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  if (!user.roles?.includes('admin')) return <Navigate to="/home" replace />
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/"             element={<Navigate to="/login" replace />} />
        <Route path="/login"        element={<Login />} />
        <Route path="/register"     element={<Register />} />
        <Route
          path="/select-sport"
          element={<ProtectedRoute><SportSelect /></ProtectedRoute>}
        />
        <Route
          path="/home"
          element={<ProtectedRoute><Home /></ProtectedRoute>}
        />
        <Route
          path="/support"
          element={<ProtectedRoute><Support /></ProtectedRoute>}
        />
        <Route
          path="/feedback"
          element={<ProtectedRoute><Feedback /></ProtectedRoute>}
        />
        <Route
          path="/profile"
          element={<ProtectedRoute><Profile /></ProtectedRoute>}
        />
        <Route
          path="/admin/users"
          element={<AdminRoute><UserManagement /></AdminRoute>}
        />

        {/* Players — list */}
        <Route
          path="/players"
          element={<ProtectedRoute><PlayersList /></ProtectedRoute>}
        />

        {/* Players — per-player nested tabs */}
        <Route
          path="/players/:id"
          element={<ProtectedRoute><PlayerLayout /></ProtectedRoute>}
        >
          <Route index element={<Navigate to="biometrics" replace />} />
          <Route path="biometrics" element={<PlayerBiometrics />} />
          <Route path="training"   element={<PlayerTraining />} />
          <Route path="physical"   element={<PlayerPhysical />} />
          <Route path="injuries"   element={<PlayerInjuries />} />
          <Route path="wellness"   element={<PlayerWellness />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </AuthProvider>
  )
}
