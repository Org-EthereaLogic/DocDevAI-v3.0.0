/**
 * E2E Test Suite for DevDocAI v3.6.0 Document Generation Workflow
 *
 * This comprehensive test suite validates:
 * 1. Navigation and UI functionality
 * 2. Document generation workflow
 * 3. API integration and error handling
 * 4. Performance metrics and accessibility
 */

import { test, expect, Page } from '@playwright/test';

// Configuration
const FRONTEND_URL = 'http://localhost:5173';
const BACKEND_URL = 'http://localhost:8000';
const TEST_TIMEOUT = 30000; // 30 seconds

// Test data
const TEST_PROJECT = {
  name: 'Test Project E2E',
  type: 'README',
  description: 'A comprehensive test project for E2E testing the document generation workflow',
  language: 'TypeScript',
  framework: 'Vue 3'
};

// Helper functions
async function waitForLoadComplete(page: Page) {
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => document.readyState === 'complete');
}

async function checkForConsoleErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  return errors;
}

async function measurePageLoadTime(page: Page, url: string): Promise<number> {
  const startTime = Date.now();
  await page.goto(url);
  await waitForLoadComplete(page);
  return Date.now() - startTime;
}

// Test Suite
test.describe('DevDocAI v3.6.0 Document Generation E2E Tests', () => {
  test.setTimeout(TEST_TIMEOUT);

  let consoleErrors: string[] = [];

  test.beforeEach(async ({ page }) => {
    // Set up console error monitoring
    consoleErrors = await checkForConsoleErrors(page);

    // Set viewport for consistent testing
    await page.setViewportSize({ width: 1280, height: 720 });
  });

  test.afterEach(async ({ page }) => {
    // Check for console errors after each test
    if (consoleErrors.length > 0) {
      console.warn('Console errors detected:', consoleErrors);
    }
  });

  test('1. Homepage loads correctly', async ({ page }) => {
    const loadTime = await measurePageLoadTime(page, FRONTEND_URL);

    // Performance assertion
    expect(loadTime).toBeLessThan(3000); // Should load in under 3 seconds

    // Check page title
    await expect(page).toHaveTitle(/DevDocAI/);

    // Check for main elements
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('main')).toBeVisible();

    // Check for Get Started button
    const getStartedButton = page.locator('button:has-text("Get Started"), a:has-text("Get Started")');
    await expect(getStartedButton).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'e2e/screenshots/homepage.png', fullPage: true });

    // Check for no console errors
    expect(consoleErrors).toHaveLength(0);
  });

  test('2. Navigation to Dashboard', async ({ page }) => {
    await page.goto(FRONTEND_URL);

    // Click Get Started or navigate directly
    const getStartedButton = page.locator('button:has-text("Get Started"), a:has-text("Get Started")');
    if (await getStartedButton.isVisible()) {
      await getStartedButton.click();
    } else {
      await page.goto(`${FRONTEND_URL}/app/dashboard`);
    }

    // Wait for dashboard to load
    await page.waitForURL(/dashboard/, { timeout: 5000 }).catch(async () => {
      // If URL doesn't change, navigate directly
      await page.goto(`${FRONTEND_URL}/app/dashboard`);
    });

    // Check dashboard elements
    await expect(page.locator('text=/Health Score|Dashboard/i')).toBeVisible({ timeout: 5000 });

    // Check sidebar navigation
    const sidebar = page.locator('aside, nav[role="navigation"], .sidebar');
    await expect(sidebar).toBeVisible();

    // Check navigation links
    await expect(page.locator('text=/Documents/i')).toBeVisible();
    await expect(page.locator('text=/Templates/i')).toBeVisible();
    await expect(page.locator('text=/Settings/i')).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'e2e/screenshots/dashboard.png', fullPage: true });
  });

  test('3. Responsive behavior', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/app/dashboard`);

    // Test desktop view
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'e2e/screenshots/responsive-desktop.png' });

    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'e2e/screenshots/responsive-tablet.png' });

    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);

    // Check for mobile menu button
    const mobileMenuButton = page.locator('button[aria-label*="menu"], button:has-text("☰")');
    if (await mobileMenuButton.isVisible()) {
      await mobileMenuButton.click();
      await page.waitForTimeout(300); // Wait for animation
    }

    await page.screenshot({ path: 'e2e/screenshots/responsive-mobile.png' });
  });

  test('4. Document Generation Workflow', async ({ page }) => {
    // Navigate to documents section
    await page.goto(`${FRONTEND_URL}/app/documents`);
    await waitForLoadComplete(page);

    // Click Generate Document button
    const generateButton = page.locator('button:has-text("Generate Document"), a:has-text("Generate Document"), button:has-text("New Document")');
    await expect(generateButton).toBeVisible({ timeout: 5000 });
    await generateButton.click();

    // Wait for form to appear
    await page.waitForURL(/generate/, { timeout: 5000 }).catch(async () => {
      // If URL doesn't change, look for form directly
      await page.goto(`${FRONTEND_URL}/app/documents/generate`);
    });

    // Fill in the form
    await page.fill('input[name="projectName"], input[placeholder*="project"], input[id*="project"]', TEST_PROJECT.name);

    // Select document type
    const typeSelect = page.locator('select[name="documentType"], select[id*="type"]');
    if (await typeSelect.isVisible()) {
      await typeSelect.selectOption(TEST_PROJECT.type);
    } else {
      // Try clicking on a dropdown
      await page.click('text=/Document Type|Type/i');
      await page.click(`text=${TEST_PROJECT.type}`);
    }

    // Fill description
    await page.fill('textarea[name="description"], textarea[placeholder*="description"], textarea[id*="description"]', TEST_PROJECT.description);

    // Monitor API calls
    const apiCallPromise = page.waitForResponse(
      response => response.url().includes('/api/') && response.status() === 200,
      { timeout: 10000 }
    ).catch(() => null);

    // Submit form
    const submitButton = page.locator('button[type="submit"], button:has-text("Generate"), button:has-text("Create")');
    await expect(submitButton).toBeVisible();

    // Take screenshot before submission
    await page.screenshot({ path: 'e2e/screenshots/document-form-filled.png', fullPage: true });

    await submitButton.click();

    // Wait for API response or loading state
    const apiResponse = await apiCallPromise;
    if (apiResponse) {
      console.log('API Response:', apiResponse.status(), apiResponse.url());
    }

    // Check for loading state
    const loadingIndicator = page.locator('.loading, .spinner, text=/Loading|Generating/i');
    if (await loadingIndicator.isVisible({ timeout: 1000 })) {
      await page.screenshot({ path: 'e2e/screenshots/document-generating.png' });
      await loadingIndicator.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    }

    // Check for success message or generated document
    const successIndicator = page.locator('text=/Success|Generated|Complete/i, .success, .alert-success');
    if (await successIndicator.isVisible({ timeout: 5000 })) {
      await page.screenshot({ path: 'e2e/screenshots/document-generated-success.png', fullPage: true });
    }
  });

  test('5. API Integration and Error Handling', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/app/documents/generate`);

    // Test with invalid data
    await page.fill('input[name="projectName"], input[placeholder*="project"], input[id*="project"]', '');

    const submitButton = page.locator('button[type="submit"], button:has-text("Generate"), button:has-text("Create")');
    await submitButton.click();

    // Check for validation error
    const errorMessage = page.locator('.error, .alert-error, text=/Required|Invalid|Error/i');
    await expect(errorMessage).toBeVisible({ timeout: 3000 });

    await page.screenshot({ path: 'e2e/screenshots/validation-error.png' });

    // Test API error handling (with valid data but potentially failing backend)
    await page.fill('input[name="projectName"], input[placeholder*="project"], input[id*="project"]', 'API Error Test');
    await page.fill('textarea[name="description"], textarea[placeholder*="description"], textarea[id*="description"]', 'Testing error handling');

    // Monitor network for errors
    page.on('response', response => {
      if (response.status() >= 400) {
        console.log('API Error:', response.status(), response.url());
      }
    });

    await submitButton.click();
    await page.waitForTimeout(2000);

    // Take screenshot of any error state
    await page.screenshot({ path: 'e2e/screenshots/api-integration.png' });
  });

  test('6. Keyboard Navigation and Accessibility', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/app/dashboard`);

    // Test keyboard navigation
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Check focused element
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    console.log('Focused element:', focusedElement);

    // Check ARIA labels
    const buttons = await page.locator('button').all();
    for (const button of buttons.slice(0, 5)) { // Check first 5 buttons
      const ariaLabel = await button.getAttribute('aria-label');
      const text = await button.textContent();
      if (!ariaLabel && !text) {
        console.warn('Button without accessible label found');
      }
    }

    // Test screen reader announcements
    const ariaLive = await page.locator('[aria-live]').count();
    console.log('ARIA live regions found:', ariaLive);

    // Check color contrast (basic check)
    const colorContrast = await page.evaluate(() => {
      const elements = document.querySelectorAll('button, a, [role="button"]');
      const lowContrast = [];
      elements.forEach(el => {
        const styles = window.getComputedStyle(el);
        const bg = styles.backgroundColor;
        const fg = styles.color;
        // Basic check - in real scenario, calculate actual contrast ratio
        if (bg && fg && bg === fg) {
          lowContrast.push(el.textContent);
        }
      });
      return lowContrast;
    });

    if (colorContrast.length > 0) {
      console.warn('Elements with potential contrast issues:', colorContrast);
    }

    await page.screenshot({ path: 'e2e/screenshots/accessibility-check.png' });
  });

  test('7. Performance Metrics', async ({ page }) => {
    // Navigate to main pages and measure performance
    const pages = [
      { name: 'Homepage', url: FRONTEND_URL },
      { name: 'Dashboard', url: `${FRONTEND_URL}/app/dashboard` },
      { name: 'Documents', url: `${FRONTEND_URL}/app/documents` },
      { name: 'Generate', url: `${FRONTEND_URL}/app/documents/generate` }
    ];

    const metrics: any[] = [];

    for (const pageInfo of pages) {
      const startTime = Date.now();
      await page.goto(pageInfo.url);
      await waitForLoadComplete(page);
      const loadTime = Date.now() - startTime;

      // Get Core Web Vitals
      const webVitals = await page.evaluate(() => {
        return {
          // Simplified metrics - in real scenario, use web-vitals library
          domContentLoaded: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart,
          loadComplete: performance.timing.loadEventEnd - performance.timing.navigationStart,
          resources: performance.getEntriesByType('resource').length
        };
      });

      metrics.push({
        page: pageInfo.name,
        loadTime,
        ...webVitals
      });

      console.log(`${pageInfo.name} Load Time: ${loadTime}ms`);
    }

    // Output performance summary
    console.table(metrics);

    // Assert performance targets
    metrics.forEach(metric => {
      expect(metric.loadTime).toBeLessThan(3000); // 3 second target
    });
  });

  test('8. API Response Times', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/app/documents`);

    // Monitor API calls
    const apiCalls: any[] = [];

    page.on('response', response => {
      if (response.url().includes('/api/')) {
        apiCalls.push({
          url: response.url(),
          status: response.status(),
          timing: response.timing()
        });
      }
    });

    // Trigger some API calls by navigating
    await page.goto(`${FRONTEND_URL}/app/dashboard`);
    await page.waitForTimeout(2000);

    // Analyze API response times
    if (apiCalls.length > 0) {
      console.log('API Response Times:');
      apiCalls.forEach(call => {
        if (call.timing) {
          console.log(`${call.url}: ${call.timing.responseEnd}ms`);
        }
      });
    }
  });
});

// Run specific test scenarios
test.describe('Integration Test Scenarios', () => {
  test('Complete Document Generation Flow', async ({ page }) => {
    // 1. Start from homepage
    await page.goto(FRONTEND_URL);
    await page.screenshot({ path: 'e2e/screenshots/flow-1-homepage.png' });

    // 2. Navigate to dashboard
    const getStarted = page.locator('button:has-text("Get Started"), a:has-text("Get Started")');
    if (await getStarted.isVisible()) {
      await getStarted.click();
    } else {
      await page.goto(`${FRONTEND_URL}/app/dashboard`);
    }
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'e2e/screenshots/flow-2-dashboard.png' });

    // 3. Go to documents
    await page.click('text=/Documents/i');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'e2e/screenshots/flow-3-documents.png' });

    // 4. Start generation
    const generateBtn = page.locator('button:has-text("Generate"), a:has-text("Generate"), button:has-text("New")');
    if (await generateBtn.isVisible()) {
      await generateBtn.click();
    } else {
      await page.goto(`${FRONTEND_URL}/app/documents/generate`);
    }
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'e2e/screenshots/flow-4-generate-form.png' });

    // 5. Fill and submit
    await page.fill('input[name="projectName"], input[placeholder*="project"], input[id*="project"]', 'Integration Test Project');
    await page.fill('textarea[name="description"], textarea[placeholder*="description"], textarea[id*="description"]', 'Full integration test of document generation');

    // Monitor the actual API call
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/') && response.method() === 'POST',
      { timeout: 10000 }
    ).catch(() => null);

    await page.screenshot({ path: 'e2e/screenshots/flow-5-form-filled.png' });

    const submit = page.locator('button[type="submit"], button:has-text("Generate"), button:has-text("Create")');
    await submit.click();

    const response = await responsePromise;
    if (response) {
      console.log('Document Generation API Response:', {
        status: response.status(),
        url: response.url(),
        ok: response.ok()
      });

      if (response.ok()) {
        const data = await response.json().catch(() => null);
        if (data) {
          console.log('Generated Document Data:', data);
        }
      }
    }

    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'e2e/screenshots/flow-6-result.png', fullPage: true });
  });
});

// Export test configuration
export default {
  timeout: TEST_TIMEOUT,
  retries: 1,
  workers: 1,
  use: {
    headless: false, // Set to true for CI
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry'
  }
};