import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { listUsers, deleteUser } from '../api/auth'

const BG = 'from-emerald-950 via-emerald-900 to-green-800'

const ROLE_BADGE = {
  admin:  'bg-purple-500/20 text-purple-300',
  coach:  'bg-blue-500/20 text-blue-300',
  player: 'bg-amber-500/20 text-amber-300',
}

const DOTS = [
  { top: '7%',  left: '5%',  delay: '0s',   size: 5 },
  { top: '22%', left: '91%', delay: '0.8s', size: 6 },
  { top: '55%', left: '3%',  delay: '1.2s', size: 4 },
  { top: '78%', left: '90%', delay: '0.4s', size: 7 },
]

export default function AdminUsers() {
  const navigate = useNavigate()
  const [users,    setUsers]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [deleting, setDeleting] = useState(null)
  const [search,   setSearch]   = useState('')
  const [filter,   setFilter]   = useState('all')

  useEffect(() => {
    listUsers()
      .then(r => setUsers(r.data))
      .catch(() => toast.error('Failed to load users'))
      .finally(() => setLoading(false))
  }, [])

  const handleDelete = async (user) => {
    if (!window.confirm(`Delete user "${user.username}"? This cannot be undone.`)) return
    setDeleting(user.id)
    try {
      await deleteUser(user.id)
      setUsers(u => u.filter(x => x.id !== user.id))
      toast.success(`User "${user.username}" deleted`)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to delete user')
    } finally {
      setDeleting(null)
    }
  }

  const visible = users.filter(u => {
    const matchRole = filter === 'all' || u.roles.includes(filter)
    const q = search.toLowerCase()
    const matchSearch = !q ||
      u.username?.toLowerCase().includes(q) ||
      u.email?.toLowerCase().includes(q) ||
      u.club?.toLowerCase().includes(q)
    return matchRole && matchSearch
  })

  const counts = {
    all:    users.length,
    admin:  users.filter(u => u.roles.includes('admin')).length,
    coach:  users.filter(u => u.roles.includes('coach')).length,
    player: users.filter(u => u.roles.includes('player')).length,
  }

  return (
    <>
      <style>{`
        @keyframes float  { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }
        @keyframes slideUp{ from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        .dot-float { animation: float 4s ease-in-out infinite; }
        .slide-up  { animation: slideUp 0.5s ease both; }
      `}</style>

      <div className={`min-h-screen bg-gradient-to-br ${BG} p-4 sm:p-6 relative overflow-hidden`}>

        {DOTS.map((d, i) => (
          <div key={i} className="dot-float absolute rounded-full bg-white pointer-events-none"
            style={{ top: d.top, left: d.left, width: d.size, height: d.size, opacity: 0.12, animationDelay: d.delay }}
          />
        ))}

        <div className="relative z-10 max-w-lg lg:max-w-4xl mx-auto pt-4">

          {/* Header */}
          <div className="slide-up flex flex-wrap items-center justify-between gap-4 mb-8">
            <div className="flex items-center gap-4">
              <button onClick={() => navigate('/home')} className="text-white/40 hover:text-white/80 transition-colors text-sm">
                ← Back
              </button>
              <div>
                <h1 className="text-2xl font-bold text-white">All Users</h1>
                <p className="text-xs text-white/40 mt-0.5">{users.length} accounts in the platform</p>
              </div>
            </div>
            <button
              onClick={() => navigate('/admin/create-user')}
              className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white text-xs font-semibold transition-all"
            >
              + Create user
            </button>
          </div>

          {/* Filters */}
          <div className="slide-up flex flex-wrap items-center gap-3 mb-5">
            {/* Search */}
            <input
              type="text"
              placeholder="Search by name, email or club…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="flex-1 min-w-[180px] bg-white/10 border border-white/20 rounded-xl px-4 py-2 text-sm text-white placeholder-white/30 outline-none focus:ring-2 focus:ring-emerald-500"
            />
            {/* Role tabs */}
            <div className="flex gap-1">
              {['all', 'admin', 'coach', 'player'].map(r => (
                <button
                  key={r}
                  onClick={() => setFilter(r)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    filter === r
                      ? 'bg-white/20 text-white'
                      : 'text-white/40 hover:text-white hover:bg-white/10'
                  }`}
                >
                  {r.charAt(0).toUpperCase() + r.slice(1)}
                  <span className="ml-1.5 text-white/30">{counts[r]}</span>
                </button>
              ))}
            </div>
          </div>

          {/* User list */}
          {loading ? (
            <p className="text-white/40 text-sm">Loading…</p>
          ) : visible.length === 0 ? (
            <p className="text-white/30 text-sm text-center py-10">No users found.</p>
          ) : (
            <div className="space-y-2">
              {visible.map(u => (
                <div
                  key={u.id}
                  className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-white/8 border border-white/10 hover:bg-white/12 transition-all"
                >
                  {/* Avatar initials */}
                  <div className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                    <span className="text-sm font-bold text-white/70">
                      {(u.username || '?')[0].toUpperCase()}
                    </span>
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold text-white truncate">{u.username}</p>
                      {u.roles.map(r => (
                        <span key={r} className={`text-xs px-2 py-0.5 rounded-full ${ROLE_BADGE[r] || 'bg-white/10 text-white/50'}`}>
                          {r}
                        </span>
                      ))}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      <p className="text-xs text-white/40 truncate">{u.email}</p>
                      {u.club && (
                        <span className="text-xs text-white/30">· {u.club}</span>
                      )}
                    </div>
                  </div>

                  {/* Delete */}
                  <button
                    onClick={() => handleDelete(u)}
                    disabled={deleting === u.id}
                    className="shrink-0 px-3 py-1.5 rounded-lg text-xs text-white/30 hover:text-red-400 hover:bg-red-500/10 transition-all disabled:opacity-40"
                  >
                    {deleting === u.id ? '…' : 'Delete'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
