import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, BookOpen, Trash2, Play, AlertCircle } from 'lucide-react'
import { manualApi, Manual } from '../services/api'

export default function ManualDetail() {
  const { manualId } = useParams<{ manualId: string }>()
  const navigate = useNavigate()
  const [manual, setManual] = useState<Manual | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (manualId) {
      loadManual(manualId)
    }
  }, [manualId])

  const loadManual = async (id: string) => {
    try {
      setLoading(true)
      const data = await manualApi.get(id)
      setManual(data)
    } catch (err) {
      setError('Manual not found')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!manual || !confirm('Are you sure you want to delete this manual?')) return

    try {
      await manualApi.delete(manual.manual_id)
      navigate('/manuals')
    } catch (err) {
      alert('Failed to delete manual. It may have active sessions.')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error || !manual) {
    return (
      <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-center gap-2">
        <AlertCircle className="w-5 h-5" />
        {error || 'Manual not found'}
      </div>
    )
  }

  return (
    <div>
      <Link
        to="/manuals"
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Manuals
      </Link>

      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <BookOpen className="w-8 h-8 text-blue-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">{manual.title}</h1>
              <p className="text-gray-500">{manual.manual_id}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Link
              to={`/sessions/create?manual_id=${manual.manual_id}`}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <Play className="w-4 h-4" />
              Start Session
            </Link>
            <button
              onClick={handleDelete}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Total Steps:</span>
            <span className="ml-2 font-medium">{manual.total_steps}</span>
          </div>
          <div>
            <span className="text-gray-500">Created:</span>
            <span className="ml-2 font-medium">
              {new Date(manual.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>

      <h2 className="text-lg font-semibold mb-4">Steps</h2>
      <div className="space-y-4">
        {manual.steps
          .sort((a, b) => a.step_number - b.step_number)
          .map((step) => (
            <div
              key={step.id}
              className="bg-white rounded-lg shadow-sm border p-6"
            >
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-semibold flex-shrink-0">
                  {step.step_number}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-lg mb-2">{step.title}</h3>
                  <p className="text-gray-600 whitespace-pre-wrap">{step.content}</p>
                </div>
              </div>
            </div>
          ))}
      </div>
    </div>
  )
}
