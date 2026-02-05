import { useState, useEffect } from 'react'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { ArrowLeft, AlertCircle } from 'lucide-react'
import { sessionApi, manualApi, Manual } from '../services/api'

export default function CreateSession() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const preselectedManual = searchParams.get('manual_id')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [manuals, setManuals] = useState<Manual[]>([])
  const [loadingManuals, setLoadingManuals] = useState(true)

  const [sessionId, setSessionId] = useState(`session-${Date.now()}`)
  const [userId, setUserId] = useState('')
  const [manualId, setManualId] = useState(preselectedManual || '')

  useEffect(() => {
    loadManuals()
  }, [])

  const loadManuals = async () => {
    try {
      const data = await manualApi.list()
      setManuals(data.manuals)
      if (data.manuals.length > 0 && !manualId) {
        setManualId(data.manuals[0].manual_id)
      }
    } catch (err) {
      setError('Failed to load manuals')
    } finally {
      setLoadingManuals(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!sessionId.trim() || !userId.trim() || !manualId) {
      setError('All fields are required')
      return
    }

    try {
      setLoading(true)
      await sessionApi.create({
        session_id: sessionId.trim(),
        user_id: userId.trim(),
        manual_id: manualId,
      })
      navigate(`/sessions/${sessionId}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create session')
    } finally {
      setLoading(false)
    }
  }

  const selectedManual = manuals.find(m => m.manual_id === manualId)

  return (
    <div className="max-w-xl mx-auto">
      <Link
        to="/sessions"
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Sessions
      </Link>

      <h1 className="text-2xl font-bold mb-6">Start New Session</h1>

      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-center gap-2 mb-6">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {manuals.length === 0 && !loadingManuals ? (
        <div className="bg-yellow-50 text-yellow-700 p-4 rounded-lg mb-6">
          <p className="font-medium mb-2">No manuals available</p>
          <p className="text-sm">
            You need to create a manual first before starting a session.{' '}
            <Link to="/manuals/create" className="underline">Create Manual</Link>
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          <div className="bg-white rounded-lg shadow-sm border p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Session ID
              </label>
              <input
                type="text"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                placeholder="e.g., session-123"
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
              <p className="text-xs text-gray-500 mt-1">Unique identifier for this session</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                User ID
              </label>
              <input
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="e.g., user-123"
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Manual
              </label>
              <select
                value={manualId}
                onChange={(e) => setManualId(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
                disabled={loadingManuals}
              >
                <option value="">Select a manual...</option>
                {manuals.map((manual) => (
                  <option key={manual.id} value={manual.manual_id}>
                    {manual.title} ({manual.total_steps} steps)
                  </option>
                ))}
              </select>
            </div>

            {selectedManual && (
              <div className="bg-blue-50 rounded-lg p-4">
                <h3 className="font-medium text-blue-900 mb-2">{selectedManual.title}</h3>
                <p className="text-sm text-blue-700">
                  This manual has {selectedManual.total_steps} steps. The session will start at step 1.
                </p>
              </div>
            )}

            <div className="flex gap-4 pt-4">
              <button
                type="submit"
                disabled={loading || loadingManuals || manuals.length === 0}
                className="flex-1 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Start Session'}
              </button>
              <Link
                to="/sessions"
                className="px-6 py-3 border rounded-lg hover:bg-gray-50 transition-colors text-center"
              >
                Cancel
              </Link>
            </div>
          </div>
        </form>
      )}
    </div>
  )
}
