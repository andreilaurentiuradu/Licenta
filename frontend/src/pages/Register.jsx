import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'
import toast from 'react-hot-toast'

export default function Register() {
  const { login }   = useAuth()
  const navigate    = useNavigate()
  const [loading,   setLoading]  = useState(false)
  const [form, setForm] = useState({
    username: '', email: '', password: '', confirm: '', role: 'coach',
  })

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password !== form.confirm) {
      toast.error('Passwords do not match')
      return
    }
    setLoading(true)
    try {
      await register({ username: form.username, email: form.email, password: form.password, role: form.role })
      await login(form.username, form.password)
      toast.success('Account created!')
      navigate('/home')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 w-full max-w-sm p-8">

        <h1 className="text-xl font-semibold text-slate-800 mb-1">Create account</h1>
        <p className="text-sm text-slate-400 mb-6">SportAnalytics Platform</p>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Username</label>
            <input
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300"
              value={form.username}
              onChange={(e) => set('username', e.target.value)}
              required minLength={3}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Email</label>
            <input
              type="email"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300"
              value={form.email}
              onChange={(e) => set('email', e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Password</label>
            <input
              type="password"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300"
              value={form.password}
              onChange={(e) => set('password', e.target.value)}
              required minLength={6}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Confirm password</label>
            <input
              type="password"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300"
              value={form.confirm}
              onChange={(e) => set('confirm', e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
            <select
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300 bg-white"
              value={form.role}
              onChange={(e) => set('role', e.target.value)}
            >
              <option value="coach">Coach</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-slate-800 text-white text-sm font-medium py-2 rounded-lg hover:bg-slate-700 transition-colors disabled:opacity-50 mt-1"
          >
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-xs text-slate-400 mt-5">
          Already have an account?{' '}
          <Link to="/login" className="text-slate-700 hover:underline font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
