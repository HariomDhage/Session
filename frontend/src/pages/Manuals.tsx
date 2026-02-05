import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, BookOpen, Trash2, AlertCircle } from 'lucide-react'
import { manualApi, Manual } from '../services/api'

export default function Manuals() {
  const [manuals, setManuals] = useState<Manual[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadManuals()
  }, [])

  const loadManuals = async () => {
    try {
      setLoading(true)
      const data = await manualApi.list()
      setManuals(data.manuals)
    } catch (err) {
      setError('Failed to load manuals')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (manualId: string) => {
    if (!confirm('Are you sure you want to delete this manual?')) return

    try {
      await manualApi.delete(manualId)
      setManuals(manuals.filter(m => m.manual_id !== manualId))
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

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Manuals</h1>
        <Link
          to="/manuals/create"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Manual
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-center gap-2 mb-4">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {manuals.map((manual) => (
          <div
            key={manual.id}
            className="bg-white rounded-lg shadow-sm border p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <BookOpen className="w-6 h-6 text-blue-600" />
              </div>
              <button
                onClick={() => handleDelete(manual.manual_id)}
                className="p-2 text-gray-400 hover:text-red-600 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            <Link to={`/manuals/${manual.manual_id}`}>
              <h3 className="font-semibold text-lg mb-1 hover:text-blue-600">
                {manual.title}
              </h3>
            </Link>
            <p className="text-gray-500 text-sm mb-4">{manual.manual_id}</p>

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">{manual.total_steps} steps</span>
              <Link
                to={`/manuals/${manual.manual_id}`}
                className="text-blue-600 hover:underline"
              >
                View details
              </Link>
            </div>
          </div>
        ))}
      </div>

      {manuals.length === 0 && (
        <div className="bg-white rounded-lg shadow-sm border p-12 text-center">
          <BookOpen className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No manuals yet</h3>
          <p className="text-gray-500 mb-4">Get started by creating your first instruction manual.</p>
          <Link
            to="/manuals/create"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Manual
          </Link>
        </div>
      )}
    </div>
  )
}
