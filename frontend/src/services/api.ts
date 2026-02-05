import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface ManualStep {
  id: string
  step_number: number
  title: string
  content: string
  created_at: string
}

export interface Manual {
  id: string
  manual_id: string
  title: string
  total_steps: number
  steps: ManualStep[]
  created_at: string
  updated_at: string
}

export interface Session {
  id: string
  session_id: string
  user_id: string
  manual_id: string
  current_step: number
  total_steps: number
  status: 'active' | 'completed' | 'abandoned'
  started_at: string
  ended_at: string | null
  last_activity_at: string
  duration_seconds: number | null
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  session_id: string
  message: string
  sender: 'user' | 'agent' | 'system'
  step_at_time: number | null
  created_at: string
}

export interface ProgressResponse {
  session_id: string
  user_id: string
  previous_step: number
  current_step: number
  total_steps: number
  status: string
  next_step: ManualStep | null
  feedback_sent: boolean
  message: string
}

export interface NextStepResponse {
  session_id: string
  current_step: number
  total_steps: number
  is_completed: boolean
  next_step: ManualStep | null
  message: string
}

// Manual APIs
export const manualApi = {
  list: async () => {
    const { data } = await api.get<{ manuals: Manual[]; total: number }>('/manuals')
    return data
  },

  get: async (manualId: string) => {
    const { data } = await api.get<Manual>(`/manuals/${manualId}`)
    return data
  },

  create: async (manual: {
    manual_id: string
    title: string
    steps: { step_number: number; title: string; content: string }[]
  }) => {
    const { data } = await api.post<Manual>('/manuals', manual)
    return data
  },

  delete: async (manualId: string) => {
    await api.delete(`/manuals/${manualId}`)
  },
}

// Session APIs
export const sessionApi = {
  list: async (params?: { user_id?: string; status?: string }) => {
    const { data } = await api.get<{ sessions: Session[]; total: number }>('/sessions', { params })
    return data
  },

  get: async (sessionId: string) => {
    const { data } = await api.get<Session>(`/sessions/${sessionId}`)
    return data
  },

  create: async (session: { session_id: string; user_id: string; manual_id: string }) => {
    const { data } = await api.post<Session>('/sessions', session)
    return data
  },

  update: async (sessionId: string, update: { status: string }) => {
    const { data } = await api.patch<Session>(`/sessions/${sessionId}`, update)
    return data
  },

  delete: async (sessionId: string) => {
    await api.delete(`/sessions/${sessionId}`)
  },

  getNextStep: async (sessionId: string) => {
    const { data } = await api.get<NextStepResponse>(`/sessions/${sessionId}/next-step`)
    return data
  },
}

// Message APIs
export const messageApi = {
  list: async (sessionId: string) => {
    const { data } = await api.get<{ messages: Message[]; total: number; session_id: string }>(
      `/sessions/${sessionId}/messages`
    )
    return data
  },

  create: async (sessionId: string, message: { user_id: string; message: string; sender: string }) => {
    const { data } = await api.post<Message>(`/sessions/${sessionId}/messages`, message)
    return data
  },
}

// Progress APIs
export const progressApi = {
  update: async (
    sessionId: string,
    progress: { user_id: string; current_step: number; step_status: 'DONE' | 'ONGOING'; idempotency_key?: string }
  ) => {
    const { data } = await api.post<ProgressResponse>(`/sessions/${sessionId}/progress`, progress)
    return data
  },
}

// Analytics Types
export interface AnalyticsOverview {
  sessions: {
    total: number
    active: number
    completed: number
    abandoned: number
  }
  manuals: {
    total: number
  }
  messages: {
    total: number
  }
  metrics: {
    completion_rate_percent: number
    avg_session_duration_seconds: number
  }
}

export interface PopularManual {
  manual_id: string
  title: string
  total_steps: number
  session_count: number
  completed_count: number
  completion_rate_percent: number
}

export interface RecentActivity {
  time_period_hours: number
  new_sessions: number
  completed_sessions: number
  progress_updates: number
  messages: number
}

// Analytics APIs
export const analyticsApi = {
  getOverview: async () => {
    const { data } = await api.get<AnalyticsOverview>('/analytics/overview')
    return data
  },

  getPopularManuals: async (limit: number = 5) => {
    const { data } = await api.get<PopularManual[]>('/analytics/popular-manuals', { params: { limit } })
    return data
  },

  getRecentActivity: async (hours: number = 24) => {
    const { data } = await api.get<RecentActivity>('/analytics/recent-activity', { params: { hours } })
    return data
  },
}

export default api
