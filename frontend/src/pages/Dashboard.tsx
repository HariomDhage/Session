import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BookOpen,
  Users,
  Clock,
  CheckCircle,
  AlertCircle,
  PlayCircle,
  TrendingUp,
  MessageSquare,
  Activity,
  BarChart3,
} from 'lucide-react'
import {
  sessionApi,
  manualApi,
  analyticsApi,
  Session,
  Manual,
  AnalyticsOverview,
  PopularManual,
  RecentActivity,
} from '../services/api'

export default function Dashboard() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [manuals, setManuals] = useState<Manual[]>([])
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null)
  const [popularManuals, setPopularManuals] = useState<PopularManual[]>([])
  const [recentActivity, setRecentActivity] = useState<RecentActivity | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [sessionsData, manualsData, analyticsData, popularData, activityData] = await Promise.all([
        sessionApi.list(),
        manualApi.list(),
        analyticsApi.getOverview(),
        analyticsApi.getPopularManuals(5),
        analyticsApi.getRecentActivity(24),
      ])
      setSessions(sessionsData.sessions)
      setManuals(manualsData.manuals)
      setAnalytics(analyticsData)
      setPopularManuals(popularData)
      setRecentActivity(activityData)
    } catch (err) {
      setError('Failed to load data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '-'
    if (seconds < 60) return `${Math.round(seconds)}s`
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`
    return `${Math.round(seconds / 3600)}h`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-center gap-2">
        <AlertCircle className="w-5 h-5" />
        {error}
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Primary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <BookOpen className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-gray-500 text-sm">Total Manuals</p>
              <p className="text-2xl font-bold">{analytics?.manuals.total || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <PlayCircle className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-gray-500 text-sm">Active Sessions</p>
              <p className="text-2xl font-bold">{analytics?.sessions.active || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-purple-100 rounded-lg">
              <CheckCircle className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <p className="text-gray-500 text-sm">Completed</p>
              <p className="text-2xl font-bold">{analytics?.sessions.completed || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-orange-100 rounded-lg">
              <Users className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <p className="text-gray-500 text-sm">Total Sessions</p>
              <p className="text-2xl font-bold">{analytics?.sessions.total || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 p-6 rounded-lg text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm">Completion Rate</p>
              <p className="text-3xl font-bold">{analytics?.metrics.completion_rate_percent || 0}%</p>
            </div>
            <TrendingUp className="w-10 h-10 text-blue-200" />
          </div>
          <p className="text-blue-100 text-xs mt-2">
            {analytics?.sessions.completed || 0} completed out of {analytics?.sessions.total || 0} sessions
          </p>
        </div>

        <div className="bg-gradient-to-r from-purple-500 to-purple-600 p-6 rounded-lg text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm">Avg. Session Duration</p>
              <p className="text-3xl font-bold">{formatDuration(analytics?.metrics.avg_session_duration_seconds || 0)}</p>
            </div>
            <Clock className="w-10 h-10 text-purple-200" />
          </div>
          <p className="text-purple-100 text-xs mt-2">
            Average time to complete sessions
          </p>
        </div>

        <div className="bg-gradient-to-r from-green-500 to-green-600 p-6 rounded-lg text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-100 text-sm">Total Messages</p>
              <p className="text-3xl font-bold">{analytics?.messages.total || 0}</p>
            </div>
            <MessageSquare className="w-10 h-10 text-green-200" />
          </div>
          <p className="text-green-100 text-xs mt-2">
            Conversations recorded
          </p>
        </div>
      </div>

      {/* Recent Activity (24h) */}
      {recentActivity && (
        <div className="bg-white rounded-lg shadow-sm border mb-6">
          <div className="p-4 border-b flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-600" />
            <h2 className="font-semibold">Activity (Last 24 Hours)</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 divide-x">
            <div className="p-4 text-center">
              <p className="text-2xl font-bold text-blue-600">{recentActivity.new_sessions}</p>
              <p className="text-gray-500 text-sm">New Sessions</p>
            </div>
            <div className="p-4 text-center">
              <p className="text-2xl font-bold text-green-600">{recentActivity.completed_sessions}</p>
              <p className="text-gray-500 text-sm">Completed</p>
            </div>
            <div className="p-4 text-center">
              <p className="text-2xl font-bold text-purple-600">{recentActivity.progress_updates}</p>
              <p className="text-gray-500 text-sm">Progress Updates</p>
            </div>
            <div className="p-4 text-center">
              <p className="text-2xl font-bold text-orange-600">{recentActivity.messages}</p>
              <p className="text-gray-500 text-sm">Messages</p>
            </div>
          </div>
        </div>
      )}

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Sessions */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-4 border-b flex justify-between items-center">
            <h2 className="font-semibold">Recent Sessions</h2>
            <Link to="/sessions" className="text-blue-600 text-sm hover:underline">
              View all
            </Link>
          </div>
          <div className="divide-y">
            {sessions.slice(0, 5).map((session) => (
              <Link
                key={session.id}
                to={`/sessions/${session.session_id}`}
                className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-2 h-2 rounded-full ${
                    session.status === 'active' ? 'bg-green-500' :
                    session.status === 'completed' ? 'bg-blue-500' : 'bg-gray-400'
                  }`} />
                  <div>
                    <p className="font-medium">{session.session_id}</p>
                    <p className="text-sm text-gray-500">User: {session.user_id}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">
                    Step {session.current_step} / {session.total_steps}
                  </p>
                  <p className="text-xs text-gray-500 flex items-center gap-1 justify-end">
                    <Clock className="w-3 h-3" />
                    {formatDuration(session.duration_seconds)}
                  </p>
                </div>
              </Link>
            ))}
            {sessions.length === 0 && (
              <div className="p-8 text-center text-gray-500">
                No sessions yet. <Link to="/sessions/create" className="text-blue-600 hover:underline">Create one</Link>
              </div>
            )}
          </div>
        </div>

        {/* Popular Manuals */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-4 border-b flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-purple-600" />
            <h2 className="font-semibold">Popular Manuals</h2>
          </div>
          <div className="divide-y">
            {popularManuals.map((manual) => (
              <Link
                key={manual.manual_id}
                to={`/manuals/${manual.manual_id}`}
                className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
              >
                <div>
                  <p className="font-medium">{manual.title}</p>
                  <p className="text-sm text-gray-500">{manual.total_steps} steps</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-purple-600">
                    {manual.session_count} sessions
                  </p>
                  <p className="text-xs text-gray-500">
                    {manual.completion_rate_percent}% completion
                  </p>
                </div>
              </Link>
            ))}
            {popularManuals.length === 0 && (
              <div className="p-8 text-center text-gray-500">
                No manuals with sessions yet.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Available Manuals */}
      <div className="bg-white rounded-lg shadow-sm border mt-6">
        <div className="p-4 border-b flex justify-between items-center">
          <h2 className="font-semibold">Available Manuals</h2>
          <Link to="/manuals" className="text-blue-600 text-sm hover:underline">
            View all
          </Link>
        </div>
        <div className="divide-y">
          {manuals.slice(0, 5).map((manual) => (
            <Link
              key={manual.id}
              to={`/manuals/${manual.manual_id}`}
              className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
            >
              <div>
                <p className="font-medium">{manual.title}</p>
                <p className="text-sm text-gray-500">{manual.manual_id}</p>
              </div>
              <div className="text-sm text-gray-600">
                {manual.total_steps} steps
              </div>
            </Link>
          ))}
          {manuals.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              No manuals yet. <Link to="/manuals/create" className="text-blue-600 hover:underline">Create one</Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
