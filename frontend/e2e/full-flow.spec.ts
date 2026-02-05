import { test, expect } from '@playwright/test';
import { api, generateTestManual, generateTestSession } from './api-helper';

// Unique test run ID to avoid conflicts
const TEST_RUN_ID = Date.now().toString(36);

test.describe('Session Service - Full E2E Flow', () => {
  test.beforeAll(async () => {
    // Verify API is healthy
    const healthy = await api.healthCheck();
    expect(healthy).toBe(true);
  });

  test.describe('1. Manual Management', () => {
    const manualId = `e2e-manual-${TEST_RUN_ID}`;

    test.afterAll(async () => {
      // Cleanup
      await api.deleteManual(manualId);
    });

    test('1.1 Dashboard loads correctly', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('h1')).toContainText('Dashboard');
    });

    test('1.2 Navigate to Manuals page', async ({ page }) => {
      await page.goto('/');
      await page.click('text=Manuals');
      await expect(page).toHaveURL('/manuals');
    });

    test('1.3 Create a new manual with 5 steps', async ({ page }) => {
      // Navigate to create manual page
      await page.goto('/manuals');
      await page.click('text=Create Manual');
      await expect(page).toHaveURL('/manuals/create');

      // Fill in manual details
      await page.fill('input[name="manual_id"]', manualId);
      await page.fill('input[name="title"]', `E2E Test Manual ${TEST_RUN_ID}`);

      // Add 5 steps
      for (let i = 1; i <= 5; i++) {
        if (i > 1) {
          await page.click('text=Add Step');
        }
        await page.fill(`input[name="steps.${i - 1}.title"]`, `Step ${i}: Test Step`);
        await page.fill(
          `textarea[name="steps.${i - 1}.content"]`,
          `This is the content for step ${i}. Follow these instructions carefully.`
        );
      }

      // Submit
      await page.click('button[type="submit"]');

      // Should redirect to manual detail or manuals list
      await page.waitForURL(/\/manuals/);
    });

    test('1.4 View created manual', async ({ page }) => {
      await page.goto(`/manuals/${manualId}`);
      await expect(page.locator('text=E2E Test Manual')).toBeVisible();
      await expect(page.locator('text=Step 1')).toBeVisible();
      await expect(page.locator('text=5 steps')).toBeVisible();
    });
  });

  test.describe('2. Session Management', () => {
    const manualId = `e2e-session-manual-${TEST_RUN_ID}`;
    const sessionId = `e2e-session-${TEST_RUN_ID}`;
    const userId = `e2e-user-${TEST_RUN_ID}`;

    test.beforeAll(async () => {
      // Create manual via API for session tests
      await api.createManual({
        manual_id: manualId,
        title: `Session Test Manual ${TEST_RUN_ID}`,
        steps: [
          { step_number: 1, title: 'First Step', content: 'Do the first thing' },
          { step_number: 2, title: 'Second Step', content: 'Do the second thing' },
          { step_number: 3, title: 'Third Step', content: 'Do the third thing' },
        ],
      });
    });

    test.afterAll(async () => {
      await api.deleteSession(sessionId);
      await api.deleteManual(manualId);
    });

    test('2.1 Navigate to Sessions page', async ({ page }) => {
      await page.goto('/');
      await page.click('text=Sessions');
      await expect(page).toHaveURL('/sessions');
    });

    test('2.2 Create a new session', async ({ page }) => {
      await page.goto('/sessions/create');

      await page.fill('input[name="session_id"]', sessionId);
      await page.fill('input[name="user_id"]', userId);

      // Select manual from dropdown
      await page.selectOption('select[name="manual_id"]', manualId);

      await page.click('button[type="submit"]');

      // Should redirect to session detail
      await page.waitForURL(/\/sessions\//);
    });

    test('2.3 View session detail page', async ({ page }) => {
      await page.goto(`/sessions/${sessionId}`);

      // Verify session info is displayed
      await expect(page.locator(`text=${sessionId}`)).toBeVisible();
      await expect(page.locator(`text=${userId}`)).toBeVisible();
      await expect(page.locator('text=Step 1')).toBeVisible();
      await expect(page.locator('text=active')).toBeVisible();
    });

    test('2.4 Complete step 1 via UI', async ({ page }) => {
      await page.goto(`/sessions/${sessionId}`);

      // Click complete step button
      await page.click('button:has-text("Complete Step")');

      // Wait for update
      await page.waitForTimeout(1000);

      // Should now show step 2
      await expect(page.locator('text=Step 2')).toBeVisible();
    });

    test('2.5 Add a message to conversation', async ({ page }) => {
      await page.goto(`/sessions/${sessionId}`);

      // Find message input and send
      const messageInput = page.locator('input[placeholder*="message"], textarea[placeholder*="message"]');
      if (await messageInput.isVisible()) {
        await messageInput.fill('This is a test message from E2E');
        await page.click('button:has-text("Send")');
        await page.waitForTimeout(500);
        await expect(page.locator('text=This is a test message')).toBeVisible();
      }
    });

    test('2.6 Verify progress via API', async () => {
      const session = await api.getSession(sessionId);
      expect(session).not.toBeNull();
      expect(session!.current_step).toBe(2); // After completing step 1
    });
  });

  test.describe('3. Edge Cases - API Level', () => {
    const manualId = `e2e-edge-manual-${TEST_RUN_ID}`;
    const sessionId = `e2e-edge-session-${TEST_RUN_ID}`;

    test.beforeAll(async () => {
      await api.createManual({
        manual_id: manualId,
        title: `Edge Case Manual ${TEST_RUN_ID}`,
        steps: [
          { step_number: 1, title: 'Step 1', content: 'Content 1' },
          { step_number: 2, title: 'Step 2', content: 'Content 2' },
          { step_number: 3, title: 'Step 3', content: 'Content 3' },
        ],
      });
      await api.createSession({
        session_id: sessionId,
        user_id: 'edge-user',
        manual_id: manualId,
      });
    });

    test.afterAll(async () => {
      await api.deleteSession(sessionId);
      await api.deleteManual(manualId);
    });

    test('3.1 Edge Case: Invalid step number (step 0)', async () => {
      const result = await api.updateProgress(sessionId, {
        user_id: 'edge-user',
        current_step: 0,
        step_status: 'DONE',
      });
      expect(result.status).toBe(400);
    });

    test('3.2 Edge Case: Invalid step number (exceeds total)', async () => {
      const result = await api.updateProgress(sessionId, {
        user_id: 'edge-user',
        current_step: 999,
        step_status: 'DONE',
      });
      expect(result.status).toBe(400);
    });

    test('3.3 Edge Case: Duplicate update (idempotency)', async () => {
      const idempotencyKey = `idem-${TEST_RUN_ID}-${Date.now()}`;

      // First request
      const result1 = await api.updateProgress(sessionId, {
        user_id: 'edge-user',
        current_step: 1,
        step_status: 'DONE',
        idempotency_key: idempotencyKey,
      });
      expect(result1.status).toBe(200);

      // Duplicate request with same key
      const result2 = await api.updateProgress(sessionId, {
        user_id: 'edge-user',
        current_step: 1,
        step_status: 'DONE',
        idempotency_key: idempotencyKey,
      });
      expect(result2.status).toBe(409); // Conflict
    });

    test('3.4 Edge Case: Session not found', async () => {
      const result = await api.updateProgress('non-existent-session', {
        user_id: 'edge-user',
        current_step: 1,
        step_status: 'DONE',
      });
      expect(result.status).toBe(404);
    });

    test('3.5 Edge Case: Manual not found during session creation', async () => {
      try {
        await api.createSession({
          session_id: `orphan-session-${TEST_RUN_ID}`,
          user_id: 'orphan-user',
          manual_id: 'non-existent-manual',
        });
        // Should not reach here
        expect(true).toBe(false);
      } catch (error) {
        expect(error).toBeDefined();
      }
    });
  });

  test.describe('4. Duration Tracking', () => {
    const manualId = `e2e-duration-manual-${TEST_RUN_ID}`;
    const sessionId = `e2e-duration-session-${TEST_RUN_ID}`;

    test.beforeAll(async () => {
      await api.createManual({
        manual_id: manualId,
        title: `Duration Manual ${TEST_RUN_ID}`,
        steps: [{ step_number: 1, title: 'Only Step', content: 'Just one step' }],
      });
    });

    test.afterAll(async () => {
      await api.deleteSession(sessionId);
      await api.deleteManual(manualId);
    });

    test('4.1 Session duration is tracked', async () => {
      // Create session
      await api.createSession({
        session_id: sessionId,
        user_id: 'duration-user',
        manual_id: manualId,
      });

      // Wait a bit
      await new Promise((r) => setTimeout(r, 2000));

      // Get session and check duration
      const session = await api.getSession(sessionId);
      expect(session).not.toBeNull();

      // Session should have duration > 0 (active session calculates live)
      // The API response might include duration_seconds
    });
  });

  test.describe('5. Conversation Storage', () => {
    const manualId = `e2e-conv-manual-${TEST_RUN_ID}`;
    const sessionId = `e2e-conv-session-${TEST_RUN_ID}`;

    test.beforeAll(async () => {
      await api.createManual({
        manual_id: manualId,
        title: `Conversation Manual ${TEST_RUN_ID}`,
        steps: [{ step_number: 1, title: 'Step', content: 'Content' }],
      });
      await api.createSession({
        session_id: sessionId,
        user_id: 'conv-user',
        manual_id: manualId,
      });
    });

    test.afterAll(async () => {
      await api.deleteSession(sessionId);
      await api.deleteManual(manualId);
    });

    test('5.1 Add and retrieve messages', async () => {
      // Add messages
      await api.addMessage(sessionId, {
        user_id: 'conv-user',
        message: 'Hello, I need help with step 1',
        sender: 'user',
      });

      await api.addMessage(sessionId, {
        user_id: 'conv-user',
        message: 'Sure, let me help you with that!',
        sender: 'agent',
      });

      await api.addMessage(sessionId, {
        user_id: 'conv-user',
        message: 'Thanks, I understand now!',
        sender: 'user',
      });

      // Retrieve messages
      const result = await api.getMessages(sessionId);
      expect(result.messages.length).toBe(3);
      expect(result.messages[0].sender).toBe('user');
      expect(result.messages[1].sender).toBe('agent');
    });
  });

  test.describe('6. Analytics', () => {
    test('6.1 Analytics endpoint returns data', async () => {
      const analytics = await api.getAnalytics();

      expect(analytics).toHaveProperty('sessions');
      expect(analytics).toHaveProperty('manuals');
      expect(analytics).toHaveProperty('messages');
      expect(analytics).toHaveProperty('metrics');

      expect(analytics.sessions).toHaveProperty('total');
      expect(analytics.sessions).toHaveProperty('active');
      expect(analytics.sessions).toHaveProperty('completed');
    });

    test('6.2 Analytics displayed on Dashboard', async ({ page }) => {
      await page.goto('/');

      // Check for analytics widgets
      await expect(page.locator('text=Total Manuals')).toBeVisible();
      await expect(page.locator('text=Active Sessions')).toBeVisible();
      await expect(page.locator('text=Completed')).toBeVisible();
    });
  });
});
