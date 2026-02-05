/**
 * API Helper for E2E Tests
 * Direct API calls for test setup and verification
 */

const API_BASE = 'http://localhost:8000/api/v1';

export interface Manual {
  id: string;
  manual_id: string;
  title: string;
  total_steps: number;
}

export interface Session {
  id: string;
  session_id: string;
  user_id: string;
  manual_id: string;
  current_step: number;
  total_steps: number;
  status: string;
}

export const api = {
  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      const res = await fetch('http://localhost:8000/health');
      return res.ok;
    } catch {
      return false;
    }
  },

  // Manual operations
  async createManual(data: {
    manual_id: string;
    title: string;
    steps: { step_number: number; title: string; content: string }[];
  }): Promise<Manual> {
    const res = await fetch(`${API_BASE}/manuals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const error = await res.text();
      throw new Error(`Failed to create manual: ${error}`);
    }
    return res.json();
  },

  async getManual(manualId: string): Promise<Manual | null> {
    const res = await fetch(`${API_BASE}/manuals/${manualId}`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`Failed to get manual: ${res.statusText}`);
    return res.json();
  },

  async deleteManual(manualId: string): Promise<void> {
    await fetch(`${API_BASE}/manuals/${manualId}`, { method: 'DELETE' });
  },

  // Session operations
  async createSession(data: {
    session_id: string;
    user_id: string;
    manual_id: string;
  }): Promise<Session> {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const error = await res.text();
      throw new Error(`Failed to create session: ${error}`);
    }
    return res.json();
  },

  async getSession(sessionId: string): Promise<Session | null> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`Failed to get session: ${res.statusText}`);
    return res.json();
  },

  async deleteSession(sessionId: string): Promise<void> {
    await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' });
  },

  async updateProgress(
    sessionId: string,
    data: {
      user_id: string;
      current_step: number;
      step_status: 'DONE' | 'ONGOING';
      idempotency_key?: string;
    }
  ): Promise<any> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/progress`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return { status: res.status, data: await res.json() };
  },

  async addMessage(
    sessionId: string,
    data: { user_id: string; message: string; sender: string }
  ): Promise<any> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(`Failed to add message: ${res.statusText}`);
    return res.json();
  },

  async getMessages(sessionId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
    if (!res.ok) throw new Error(`Failed to get messages: ${res.statusText}`);
    return res.json();
  },

  // Analytics
  async getAnalytics(): Promise<any> {
    const res = await fetch(`${API_BASE}/analytics/overview`);
    if (!res.ok) throw new Error(`Failed to get analytics: ${res.statusText}`);
    return res.json();
  },
};

// Test data generators
export function generateTestManual(id: string, stepCount: number = 3) {
  return {
    manual_id: `test-manual-${id}`,
    title: `Test Manual ${id}`,
    steps: Array.from({ length: stepCount }, (_, i) => ({
      step_number: i + 1,
      title: `Step ${i + 1}`,
      content: `Content for step ${i + 1}. This is test content.`,
    })),
  };
}

export function generateTestSession(id: string, manualId: string) {
  return {
    session_id: `test-session-${id}`,
    user_id: `test-user-${id}`,
    manual_id: manualId,
  };
}
