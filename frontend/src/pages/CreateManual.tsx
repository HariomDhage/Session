import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Plus, Trash2, AlertCircle, GripVertical } from 'lucide-react'
import { manualApi } from '../services/api'

interface StepForm {
  title: string
  content: string
}

export default function CreateManual() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [manualId, setManualId] = useState('')
  const [title, setTitle] = useState('')
  const [steps, setSteps] = useState<StepForm[]>([
    { title: '', content: '' },
    { title: '', content: '' },
  ])

  const addStep = () => {
    setSteps([...steps, { title: '', content: '' }])
  }

  const removeStep = (index: number) => {
    if (steps.length <= 2) {
      alert('A manual must have at least 2 steps')
      return
    }
    setSteps(steps.filter((_, i) => i !== index))
  }

  const updateStep = (index: number, field: keyof StepForm, value: string) => {
    const newSteps = [...steps]
    newSteps[index][field] = value
    setSteps(newSteps)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validation
    if (!manualId.trim() || !title.trim()) {
      setError('Manual ID and title are required')
      return
    }

    const emptySteps = steps.filter(s => !s.title.trim() || !s.content.trim())
    if (emptySteps.length > 0) {
      setError('All steps must have a title and content')
      return
    }

    try {
      setLoading(true)
      await manualApi.create({
        manual_id: manualId.trim(),
        title: title.trim(),
        steps: steps.map((step, index) => ({
          step_number: index + 1,
          title: step.title.trim(),
          content: step.content.trim(),
        })),
      })
      navigate('/manuals')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create manual')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <Link
        to="/manuals"
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Manuals
      </Link>

      <h1 className="text-2xl font-bold mb-6">Create New Manual</h1>

      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-center gap-2 mb-6">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <h2 className="font-semibold mb-4">Manual Details</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Manual ID
              </label>
              <input
                type="text"
                value={manualId}
                onChange={(e) => setManualId(e.target.value)}
                placeholder="e.g., python-basics"
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
              <p className="text-xs text-gray-500 mt-1">Unique identifier for this manual</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Introduction to Python"
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-semibold">Steps ({steps.length})</h2>
            <button
              type="button"
              onClick={addStep}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition-colors text-sm"
            >
              <Plus className="w-4 h-4" />
              Add Step
            </button>
          </div>

          <div className="space-y-4">
            {steps.map((step, index) => (
              <div
                key={index}
                className="border rounded-lg p-4 bg-gray-50"
              >
                <div className="flex items-center gap-3 mb-3">
                  <GripVertical className="w-4 h-4 text-gray-400" />
                  <span className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">
                    {index + 1}
                  </span>
                  <input
                    type="text"
                    value={step.title}
                    onChange={(e) => updateStep(index, 'title', e.target.value)}
                    placeholder="Step title"
                    className="flex-1 px-3 py-1.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => removeStep(index)}
                    className="p-1.5 text-gray-400 hover:text-red-600 transition-colors"
                    title="Remove step"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <textarea
                  value={step.content}
                  onChange={(e) => updateStep(index, 'content', e.target.value)}
                  placeholder="Step instructions and content..."
                  rows={3}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-4">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Create Manual'}
          </button>
          <Link
            to="/manuals"
            className="px-6 py-3 border rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  )
}
