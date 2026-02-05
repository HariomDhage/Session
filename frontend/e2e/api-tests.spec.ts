import { test, expect } from '@playwright/test';
import { api } from './api-helper';

/**
 * Pure API Tests - No UI required
 * Tests all backend endpoints and edge cases
 */

const TEST_RUN_ID = `api-${Date.now().toString(36)}`;

test.describe('API Tests - Backend Verification', () => {
  test.describe.configure({ mode: 'serial' });

  // Test data
  const manualId = `api-test-manual-${TEST_RUN_ID}`;
  const sessionId = `api-test-session-${TEST_RUN_ID}`;
  const userId = `api-test-user-${TEST_RUN_ID}`;

  test('0. Health Check', async () => {
    const healthy = await api.healthCheck();
    expect(healthy).toBe(true);
  });

  test.describe('Manual CRUD', () => {
    test('1.1 Create manual with 5 steps', async () => {
      const manual = await api.createManual({
        manual_id: manualId,
        title: 'API Test Manual',
        steps: [
          { step_number: 1, title: 'Introduction', content: 'Welcome to the course' },
          { step_number: 2, title: 'Setup', content: 'Set up your environment' },
          { step_number: 3, title: 'Basics', content: 'Learn the basics' },
          { step_number: 4, title: 'Advanced', content: 'Advanced concepts' },
          { step_number: 5, title: 'Conclusion', content: 'Wrap up' },
        ],
      });

      expect(manual.manual_id).toBe(manualId);
      expect(manual.total_steps).toBe(5);
    });

    test('1.2 Retrieve manual', async () => {
      const manual = await api.getManual(manualId);
      expect(manual).not.toBeNull();
      expect(manual!.title).toBe('API Test Manual');
    });

    test('1.3 Create duplicate manual fails', async () => {
      try {
        await api.createManual({
          manual_id: manualId,
          title: 'Duplicate',
          steps: [{ step_number: 1, title: 'Step', content: 'Content' }],
        });
        expect(true).toBe(false); // Should not reach
      } catch (error: any) {
        expect(error.message).toContain('Failed');
      }
    });
  });

  test.describe('Session CRUD', () => {
    test('2.1 Create session', async () => {
      const session = await api.createSession({
        session_id: sessionId,
        user_id: userId,
        manual_id: manualId,
      });

      expect(session.session_id).toBe(sessionId);
      expect(session.current_step).toBe(1);
      expect(session.status).toBe('active');
      expect(session.total_steps).toBe(5);
    });

    test('2.2 Retrieve session', async () => {
      const session = await api.getSession(sessionId);
      expect(session).not.toBeNull();
      expect(session!.user_id).toBe(userId);
    });

    test('2.3 Create duplicate session fails', async () => {
      try {
        await api.createSession({
          session_id: sessionId,
          user_id: userId,
          manual_id: manualId,
        });
        expect(true).toBe(false);
      } catch (error: any) {
        expect(error.message).toContain('Failed');
      }
    });
  });

  test.describe('Progress Tracking', () => {
    test('3.1 Update progress - ONGOING (no increment)', async () => {
      const result = await api.updateProgress(sessionId, {
        user_id: userId,
        current_step: 1,
        step_status: 'ONGOING',
      });

      expect(result.status).toBe(200);

      // Verify step didn't increment
      const session = await api.getSession(sessionId);
      expect(session!.current_step).toBe(1);
    });

    test('3.2 Update progress - DONE (should increment)', async () => {
      const result = await api.updateProgress(sessionId, {
        user_id: userId,
        current_step: 1,
        step_status: 'DONE',
      });

      expect(result.status).toBe(200);

      // Verify step incremented
      const session = await api.getSession(sessionId);
      expect(session!.current_step).toBe(2);
    });

    test('3.3 Complete step 2', async () => {
      await api.updateProgress(sessionId, {
        user_id: userId,
        current_step: 2,
        step_status: 'DONE',
      });

      const session = await api.getSession(sessionId);
      expect(session!.current_step).toBe(3);
    });

    test('3.4 Complete step 3', async () => {
      await api.updateProgress(sessionId, {
        user_id: userId,
        current_step: 3,
        step_status: 'DONE',
      });

      const session = await api.getSession(sessionId);
      expect(session!.current_step).toBe(4);
    });
  });

  test.describe('Conversation Storage', () => {
    test('4.1 Add user message', async () => {
      const message = await api.addMessage(sessionId, {
        user_id: userId,
        message: 'I completed step 3, what next?',
        sender: 'user',
      });

      expect(message.sender).toBe('user');
      expect(message.message).toContain('step 3');
    });

    test('4.2 Add agent message', async () => {
      const message = await api.addMessage(sessionId, {
        user_id: userId,
        message: 'Great job! Now proceed to step 4.',
        sender: 'agent',
      });

      expect(message.sender).toBe('agent');
    });

    test('4.3 Add system message', async () => {
      const message = await api.addMessage(sessionId, {
        user_id: userId,
        message: 'Progress saved automatically.',
        sender: 'system',
      });

      expect(message.sender).toBe('system');
    });

    test('4.4 Retrieve all messages', async () => {
      const result = await api.getMessages(sessionId);

      expect(result.messages.length).toBe(3);
      expect(result.total).toBe(3);

      // Verify order (oldest first)
      expect(result.messages[0].sender).toBe('user');
      expect(result.messages[1].sender).toBe('agent');
      expect(result.messages[2].sender).toBe('system');
    });
  });

  test.describe('Edge Cases', () => {
    test('5.1 Invalid step number - 0', async () => {
      const result = await api.updateProgress(sessionId, {
        user_id: userId,
        current_step: 0,
        step_status: 'DONE',
      });

      expect(result.status).toBe(400);
      expect(result.data.error?.code || result.data.detail).toBeDefined();
    });

    test('5.2 Invalid step number - exceeds total', async () => {
      const result = await api.updateProgress(sessionId, {
        user_id: userId,
        current_step: 100,
        step_status: 'DONE',
      });

      expect(result.status).toBe(400);
    });

    test('5.3 Duplicate update with idempotency key', async () => {
      const idempKey = `test-idem-${Date.now()}`;

      // First call
      const result1 = await api.updateProgress(sessionId, {
        user_id: userId,
        current_step: 4,
        step_status: 'DONE',
        idempotency_key: idempKey,
      });
      expect(result1.status).toBe(200);

      // Duplicate call with same key
      const result2 = await api.updateProgress(sessionId, {
        user_id: userId,
        current_step: 4,
        step_status: 'DONE',
        idempotency_key: idempKey,
      });
      expect(result2.status).toBe(409);
    });

    test('5.4 Session not found', async () => {
      const result = await api.updateProgress('fake-session-xyz', {
        user_id: userId,
        current_step: 1,
        step_status: 'DONE',
      });

      expect(result.status).toBe(404);
    });

    test('5.5 Manual not found for new session', async () => {
      try {
        await api.createSession({
          session_id: `orphan-${TEST_RUN_ID}`,
          user_id: userId,
          manual_id: 'non-existent-manual-xyz',
        });
        expect(true).toBe(false);
      } catch (error: any) {
        expect(error.message).toContain('Failed');
      }
    });
  });

  test.describe('Session Completion', () => {
    test('6.1 Complete remaining steps', async () => {
      // Session is at step 5, complete it
      const result = await api.updateProgress(sessionId, {
        user_id: userId,
        current_step: 5,
        step_status: 'DONE',
      });

      expect(result.status).toBe(200);
    });

    test('6.2 Verify session is completed', async () => {
      const session = await api.getSession(sessionId);
      expect(session!.status).toBe('completed');
      expect(session!.current_step).toBe(6); // Beyond total steps
    });

    test('6.3 Cannot update completed session', async () => {
      const result = await api.updateProgress(sessionId, {
        user_id: userId,
        current_step: 1,
        step_status: 'DONE',
      });

      expect(result.status).toBe(400);
    });
  });

  test.describe('Analytics', () => {
    test('7.1 Get overview stats', async () => {
      const analytics = await api.getAnalytics();

      expect(analytics.sessions.total).toBeGreaterThanOrEqual(1);
      expect(analytics.sessions.completed).toBeGreaterThanOrEqual(1);
      expect(analytics.manuals.total).toBeGreaterThanOrEqual(1);
      expect(analytics.messages.total).toBeGreaterThanOrEqual(3);
    });
  });

  test.describe('Cleanup', () => {
    test('8.1 Delete session', async () => {
      await api.deleteSession(sessionId);

      const session = await api.getSession(sessionId);
      expect(session).toBeNull();
    });

    test('8.2 Delete manual', async () => {
      await api.deleteManual(manualId);

      const manual = await api.getManual(manualId);
      expect(manual).toBeNull();
    });
  });
});
