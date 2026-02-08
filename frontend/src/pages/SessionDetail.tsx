import { useEffect, useState, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Clock,
  User,
  BookOpen,
  CheckCircle,
  AlertCircle,
  Send,
  RefreshCw,
} from 'lucide-react'
import { sessionApi, messageApi, progressApi, Session, Message, NextStepResponse } from '../services/api'

export default function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const [session, setSession] = useState<Session | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [nextStep, setNextStep] = useState<NextStepResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [newMessage, setNewMessage] = useState('')
  const [sendingMessage, setSendingMessage] = useState(false)
  const [updatingProgress, setUpdatingProgress] = useState(false)

  useEffect(() => {
    if (sessionId) {
      loadSession()
    }
  }, [sessionId])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadSession = async () => {
    if (!sessionId) return

    try {
      setLoading(true)
      const [sessionData, messagesData, nextStepData] = await Promise.all([
        sessionApi.get(sessionId),
        messageApi.list(sessionId),
        sessionApi.getNextStep(sessionId),
      ])
      setSession(sessionData)
      setMessages(messagesData.messages)
      setNextStep(nextStepData)
    } catch (err) {
      setError('Session not found')
    } finally {
      setLoading(false)
    }
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!session || !newMessage.trim()) return

    try {
      setSendingMessage(true)
      const message = await messageApi.create(session.session_id, {
        user_id: session.user_id,
        message: newMessage.trim(),
        sender: 'user',
      })
      setMessages([...messages, message])
      setNewMessage('')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to send message')
    } finally {
      setSendingMessage(false)
    }
  }

  const handleCompleteStep = async () => {
    if (!session || !nextStep || nextStep.is_completed) return

    try {
      setUpdatingProgress(true)
      const result = await progressApi.update(session.session_id, {
        user_id: session.user_id,
        current_step: nextStep.current_step,
        step_status: 'DONE',
        idempotency_key: `step-${nextStep.current_step}-${Date.now()}`,
      })

      // Reload session data
      const [sessionData, nextStepData] = await Promise.all([
        sessionApi.get(session.session_id),
        sessionApi.getNextStep(session.session_id),
      ])
      setSession(sessionData)
      setNextStep(nextStepData)

      // Add system message
      setMessages([
        ...messages,
        {
          id: `system-${Date.now()}`,
          session_id: session.session_id,
          message: result.message,
          sender: 'system',
          step_at_time: result.current_step - 1,
          created_at: new Date().toISOString(),
        },
      ])
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update progress')
    } finally {
      setUpdatingProgress(false)
    }
  }

  const handleEndSession = async (status: 'completed' | 'abandoned') => {
    if (!session) return
    if (!confirm(`Are you sure you want to ${status === 'completed' ? 'complete' : 'abandon'} this session?`)) return

    try {
      await sessionApi.update(session.session_id, { status })
      navigate('/sessions')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update session')
    }
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '0s'
    const mins = Math.floor(seconds / 60)
    const secs = Math.round(seconds % 60)
    if (mins === 0) return `${secs}s`
    return `${mins}m ${secs}s`
  }

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-center gap-2">
        <AlertCircle className="w-5 h-5" />
        {error || 'Session not found'}
      </div>
    )
  }

  const progressPercent = Math.min(100, ((session.current_step - 1) / session.total_steps) * 100)

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <Link
        to="/sessions"
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Sessions
      </Link>

      <div className="flex-1 flex gap-6 min-h-0">
        {/* Left Panel - Session Info & Progress */}
        <div className="w-80 flex flex-col gap-4">
          {/* Session Info */}
          <div className="bg-white rounded-lg shadow-sm border p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">Session Info</h2>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                session.status === 'active' ? 'bg-green-100 text-green-700' :
                session.status === 'completed' ? 'bg-blue-100 text-blue-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {session.status}
              </span>
            </div>

            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2 text-gray-600">
                <User className="w-4 h-4" />
                <span>{session.user_id}</span>
              </div>
              <div className="flex items-center gap-2 text-gray-600">
                <BookOpen className="w-4 h-4" />
                <span>{session.manual_id}</span>
              </div>
              <div className="flex items-center gap-2 text-gray-600">
                <Clock className="w-4 h-4" />
                <span>{formatDuration(session.duration_seconds)}</span>
              </div>
            </div>

            {session.status === 'active' && (
              <div className="mt-4 pt-4 border-t flex gap-2">
                <button
                  onClick={() => handleEndSession('completed')}
                  className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
                >
                  Complete
                </button>
                <button
                  onClick={() => handleEndSession('abandoned')}
                  className="flex-1 px-3 py-2 border text-gray-600 rounded-lg text-sm hover:bg-gray-50"
                >
                  Abandon
                </button>
              </div>
            )}
          </div>

          {/* Progress */}
          <div className="bg-white rounded-lg shadow-sm border p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">Progress</h2>
              <button
                onClick={loadSession}
                className="p-1 text-gray-400 hover:text-gray-600"
                title="Refresh"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            <div className="mb-4">
              <div className="flex justify-between text-sm mb-1">
                <span>Step {session.current_step > session.total_steps ? session.total_steps : session.current_step - 1} of {session.total_steps}</span>
                <span>{Math.round(progressPercent)}%</span>
              </div>
              <div className="h-3 bg-gray-200 rounded-full">
                <div
                  className="h-3 bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-500"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>

            {/* Steps indicator */}
            <div className="space-y-2">
              {Array.from({ length: session.total_steps }, (_, i) => i + 1).map((step) => {
                const isCompleted = step < session.current_step
                const isCurrent = step === session.current_step
                return (
                  <div
                    key={step}
                    className={`flex items-center gap-2 p-2 rounded ${
                      isCurrent ? 'bg-blue-50' : ''
                    }`}
                  >
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                      isCompleted ? 'bg-green-500 text-white' :
                      isCurrent ? 'bg-blue-500 text-white' :
                      'bg-gray-200 text-gray-500'
                    }`}>
                      {isCompleted ? <CheckCircle className="w-4 h-4" /> : step}
                    </div>
                    <span className={`text-sm ${isCurrent ? 'font-medium' : 'text-gray-600'}`}>
                      Step {step}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Right Panel - Current Step & Chat */}
        <div className="flex-1 flex flex-col gap-4 min-h-0">
          {/* Current Step */}
          {nextStep && !nextStep.is_completed && nextStep.next_step && (
            <div className="bg-white rounded-lg shadow-sm border p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">
                      {nextStep.next_step.step_number}
                    </span>
                    <h3 className="font-semibold">{nextStep.next_step.title}</h3>
                  </div>
                  <p className="text-gray-600 whitespace-pre-wrap">{nextStep.next_step.content}</p>
                </div>
                {session.status === 'active' && (
                  <button
                    onClick={handleCompleteStep}
                    disabled={updatingProgress}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 ml-4"
                  >
                    <CheckCircle className="w-4 h-4" />
                    {updatingProgress ? 'Completing...' : 'Mark Complete'}
                  </button>
                )}
              </div>
            </div>
          )}

          {nextStep?.is_completed && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
              <CheckCircle className="w-8 h-8 text-green-600 mx-auto mb-2" />
              <h3 className="font-semibold text-green-800">All Steps Completed!</h3>
              <p className="text-green-600 text-sm">Great job finishing this manual.</p>
            </div>
          )}

          {/* Chat */}
          <div className="flex-1 bg-white rounded-lg shadow-sm border flex flex-col min-h-0">
            <div className="p-4 border-b">
              <h2 className="font-semibold">Conversation</h2>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  No messages yet. Start the conversation!
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[70%] rounded-lg p-3 ${
                      message.sender === 'user'
                        ? 'bg-blue-600 text-white'
                        : message.sender === 'system'
                        ? 'bg-gray-100 text-gray-600 italic'
                        : 'bg-gray-200 text-gray-900'
                    }`}>
                      <p className="whitespace-pre-wrap">{message.message}</p>
                      <p className={`text-xs mt-1 ${
                        message.sender === 'user' ? 'text-blue-200' : 'text-gray-400'
                      }`}>
                        {formatTime(message.created_at)}
                        {message.step_at_time && ` • Step ${message.step_at_time}`}
                      </p>
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {session.status === 'active' && (
              <form onSubmit={handleSendMessage} className="p-4 border-t">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Type a message..."
                    className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    disabled={sendingMessage}
                  />
                  <button
                    type="submit"
                    disabled={sendingMessage || !newMessage.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
