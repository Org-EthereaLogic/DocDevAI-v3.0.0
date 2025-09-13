/**
 * E2E Tests for Document Generation Flow
 * Comprehensive user journey testing with real browser automation
 */

import { test, expect } from '@playwright/test';

test.describe('Document Generation User Journey', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');

    // Wait for the app to fully load
    await page.waitForLoadState('networkidle');
  });

  test('should generate a README document successfully', async ({ page }) => {
    // Fill out the form
    await page.fill('[data-testid="project-name-input"]', 'Test Project E2E');
    await page.fill('[data-testid="description-input"]', 'A comprehensive end-to-end testing project for validating the document generation workflow.');
    await page.fill('[data-testid="author-input"]', 'E2E Test Author');

    // Add tech stack
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js, Python, FastAPI');
    await page.click('[data-testid="add-tech-stack"]');

    // Add features
    await page.fill('[data-testid="feature-input"]', 'AI-powered generation');
    await page.click('[data-testid="add-feature"]');

    // Submit the form
    await page.click('[data-testid="submit-button"]');

    // Wait for generation to start
    await expect(page.locator('[data-testid="generation-progress"]')).toBeVisible();

    // Wait for generation to complete (with extended timeout for real API)
    await expect(page.locator('[data-testid="document-content"]')).toBeVisible({ timeout: 60000 });

    // Verify the generated document
    const documentContent = await page.locator('[data-testid="document-content"]').textContent();
    expect(documentContent).toContain('Test Project E2E');
    expect(documentContent).toContain('Vue.js');
  });

  test('should handle form validation errors', async ({ page }) => {
    // Try to submit empty form
    await page.click('[data-testid="submit-button"]');

    // Check for validation errors
    await expect(page.locator('[data-testid="project-name-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="description-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="author-error"]')).toBeVisible();

    // Verify submit button is disabled
    await expect(page.locator('[data-testid="submit-button"]')).toBeDisabled();
  });

  test('should allow canceling document generation', async ({ page }) => {
    // Fill and submit form
    await page.fill('[data-testid="project-name-input"]', 'Cancel Test Project');
    await page.fill('[data-testid="description-input"]', 'Testing cancellation functionality during generation.');
    await page.fill('[data-testid="author-input"]', 'Cancel Test Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');

    await page.click('[data-testid="submit-button"]');

    // Wait for generation to start
    await expect(page.locator('[data-testid="generation-progress"]')).toBeVisible();

    // Click cancel button
    await page.click('[data-testid="cancel-button"]');

    // Verify cancellation
    await expect(page.locator('[data-testid="generation-progress"]')).toBeHidden();
    await expect(page.locator('[data-testid="submit-button"]')).toBeEnabled();
  });

  test('should display generation progress with status updates', async ({ page }) => {
    // Fill form
    await page.fill('[data-testid="project-name-input"]', 'Progress Test');
    await page.fill('[data-testid="description-input"]', 'Testing progress indicator during generation.');
    await page.fill('[data-testid="author-input"]', 'Progress Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');

    await page.click('[data-testid="submit-button"]');

    // Check for progress indicators
    await expect(page.locator('[data-testid="generation-progress"]')).toBeVisible();
    await expect(page.locator('[data-testid="progress-bar"]')).toBeVisible();
    await expect(page.locator('[data-testid="progress-message"]')).toBeVisible();

    // Verify progress messages update
    const progressMessages = [];
    const messageLocator = page.locator('[data-testid="progress-message"]');

    // Capture progress messages
    for (let i = 0; i < 5; i++) {
      const message = await messageLocator.textContent();
      progressMessages.push(message);
      await page.waitForTimeout(1000);
    }

    // Verify we got different messages
    const uniqueMessages = [...new Set(progressMessages)];
    expect(uniqueMessages.length).toBeGreaterThan(1);
  });
});

test.describe('Document Interaction Features', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Generate a document first
    await page.fill('[data-testid="project-name-input"]', 'Interaction Test');
    await page.fill('[data-testid="description-input"]', 'Testing document interaction features.');
    await page.fill('[data-testid="author-input"]', 'Interaction Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');
    await page.click('[data-testid="submit-button"]');

    // Wait for generation
    await expect(page.locator('[data-testid="document-content"]')).toBeVisible({ timeout: 60000 });
  });

  test('should copy document content to clipboard', async ({ page, context }) => {
    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);

    // Click copy button
    await page.click('[data-testid="copy-button"]');

    // Verify visual feedback
    await expect(page.locator('[data-testid="copy-button"]')).toContainText('Copied');

    // Verify clipboard content
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toContain('Interaction Test');
  });

  test('should download document as markdown file', async ({ page }) => {
    // Start waiting for download before clicking
    const downloadPromise = page.waitForEvent('download');

    // Click download button
    await page.click('[data-testid="download-button"]');

    // Wait for download
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/interaction-test.*\.md/);

    // Verify download content
    const path = await download.path();
    expect(path).toBeTruthy();
  });

  test('should toggle between preview and source view', async ({ page }) => {
    // Initially in preview mode
    await expect(page.locator('[data-testid="document-content"]')).toBeVisible();
    await expect(page.locator('[data-testid="source-view"]')).toBeHidden();

    // Toggle to source view
    await page.click('[data-testid="preview-toggle"]');

    await expect(page.locator('[data-testid="source-view"]')).toBeVisible();
    await expect(page.locator('[data-testid="document-content"]')).toBeHidden();

    // Verify source content
    const sourceContent = await page.locator('[data-testid="source-view"]').textContent();
    expect(sourceContent).toContain('# Interaction Test');

    // Toggle back to preview
    await page.click('[data-testid="preview-toggle"]');

    await expect(page.locator('[data-testid="document-content"]')).toBeVisible();
    await expect(page.locator('[data-testid="source-view"]')).toBeHidden();
  });
});

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Intercept API calls and simulate network error
    await page.route('**/api/generate', route => route.abort());

    // Fill and submit form
    await page.fill('[data-testid="project-name-input"]', 'Network Error Test');
    await page.fill('[data-testid="description-input"]', 'Testing network error handling.');
    await page.fill('[data-testid="author-input"]', 'Error Test Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');

    await page.click('[data-testid="submit-button"]');

    // Verify error handling
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="error-message"]')).toContainText('network');
  });

  test('should handle server errors gracefully', async ({ page }) => {
    // Intercept API calls and simulate server error
    await page.route('**/api/generate', route =>
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal server error' })
      })
    );

    // Fill and submit form
    await page.fill('[data-testid="project-name-input"]', 'Server Error Test');
    await page.fill('[data-testid="description-input"]', 'Testing server error handling.');
    await page.fill('[data-testid="author-input"]', 'Server Error Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');

    await page.click('[data-testid="submit-button"]');

    // Verify error handling
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
  });

  test('should allow retry after error', async ({ page }) => {
    // First request fails
    let requestCount = 0;
    await page.route('**/api/generate', route => {
      requestCount++;
      if (requestCount === 1) {
        route.fulfill({
          status: 500,
          body: JSON.stringify({ error: 'Internal server error' })
        });
      } else {
        route.fulfill({
          status: 200,
          body: JSON.stringify({
            success: true,
            content: '# Retry Success\n\nThis worked after retry.'
          })
        });
      }
    });

    // Fill and submit form
    await page.fill('[data-testid="project-name-input"]', 'Retry Test');
    await page.fill('[data-testid="description-input"]', 'Testing retry functionality.');
    await page.fill('[data-testid="author-input"]', 'Retry Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');

    await page.click('[data-testid="submit-button"]');

    // Wait for error and retry
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible({ timeout: 10000 });
    await page.click('[data-testid="retry-button"]');

    // Verify successful retry
    await expect(page.locator('[data-testid="document-content"]')).toBeVisible({ timeout: 30000 });
    const content = await page.locator('[data-testid="document-content"]').textContent();
    expect(content).toContain('Retry Success');
  });
});

test.describe('Responsive Design', () => {
  test('should work correctly on mobile devices', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // Verify mobile layout
    const form = page.locator('[data-testid="readme-form"]');
    await expect(form).toHaveClass(/mobile-layout/);

    // Fill form on mobile
    await page.fill('[data-testid="project-name-input"]', 'Mobile Test');
    await page.fill('[data-testid="description-input"]', 'Testing mobile responsiveness.');
    await page.fill('[data-testid="author-input"]', 'Mobile Author');

    // Tech stack should be stacked vertically on mobile
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');

    const techStack = page.locator('[data-testid="tech-stack-list"]');
    await expect(techStack).toHaveClass(/flex-col/);

    // Submit and verify generation works on mobile
    await page.click('[data-testid="submit-button"]');
    await expect(page.locator('[data-testid="generation-progress"]')).toBeVisible();
  });

  test('should adapt to tablet viewport', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');

    // Verify tablet layout adaptations
    const container = page.locator('[data-testid="app-container"]');
    await expect(container).toHaveClass(/tablet-layout/);

    // Form should use appropriate spacing on tablet
    const formFields = page.locator('[data-testid="form-fields"]');
    await expect(formFields).toHaveCSS('max-width', /.*/);
  });
});
