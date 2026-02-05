import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Users, Clock, Trash2, AlertCircle, Filter } from 'lucide-react'
import { sessionApi, Session } from '../services/api'

export default function Sessions() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('')

  useEffect(() => {
    loadSessions()
  }, [statusFilter])

  const loadSessions = async () => {
    try {
      setLoading(true)
      const params = statusFilter ? { status: statusFilter } : undefined
      const data = await sessionApi.list(params)
      setSessions(data.sessions)
    } catch (err) {
      setError('Failed to load sessions')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (sessionId: string) => {
    if (!confirm('Are you sure you want to delete this session?')) return

    try {
      await sessionApi.delete(sessionId)
      setSessions(sessions.filter(s => s.session_id !== sessionId))
    } catch (err) {
      alert('Failed to delete session')
    }
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '-'
    if (seconds < 60) return `${Math.round(seconds)}s`
    if (seconds < 3600) return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`
    return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-700'
      case 'completed':
        return 'bg-blue-100 text-blue-700'
      case 'abandoned':
        return 'bg-gray-100 text-gray-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Sessions</h1>
        <Link
          to="/sessions/create"
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Session
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-center gap-2 mb-4">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border p-4 mb-6">
        <div className="flex items-center gap-4">
          <Filter className="w-4 h-4 text-gray-500" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="abandoned">Abandoned</option>
          </select>
        </div>
      </div>

      {/* Sessions Table */}
      <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Session</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">User</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Progress</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Duration</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {sessions.map((session) => (
              <tr key={session.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <Link
                    to={`/sessions/${session.session_id}`}
                    className="font-medium text-blue-600 hover:underline"
                  >
                    {session.session_id}
                  </Link>
                  <p className="text-xs text-gray-500">{session.manual_id}</p>
                </td>
                <td className="px-6 py-4 text-sm">{session.user_id}</td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-gray-200 rounded-full w-24">
                      <div
                        className="h-2 bg-blue-600 rounded-full"
                        style={{
                          width: `${Math.min(100, ((session.current_step - 1) / session.total_steps) * 100)}%`
                        }}
                      />
                    </div>
                    <span className="text-sm text-gray-600">
                      {session.current_step - 1}/{session.total_steps}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(session.status)}`}>
                    {session.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDuration(session.duration_seconds)}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/sessions/${session.session_id}`}
                      className="text-blue-600 hover:underline text-sm"
                    >
                      View
                    </Link>
                    <button
                      onClick={() => handleDelete(session.session_id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {sessions.length === 0 && (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No sessions found</h3>
            <p className="text-gray-500 mb-4">
              {statusFilter ? 'No sessions match the selected filter.' : 'Get started by creating a new session.'}
            </p>
            <Link
              to="/sessions/create"
              className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Session
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
