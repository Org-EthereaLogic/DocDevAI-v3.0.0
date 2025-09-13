import { test, expect } from '@playwright/test';

test('Debug Frontend Rendering', async ({ page }) => {
  await page.goto('http://localhost:5174');

  // Check page title
  const title = await page.title();
  console.log('Page title:', title);

  // Check page HTML content
  const htmlContent = await page.content();
  console.log('HTML Length:', htmlContent.length);

  // Check for #app element
  const appElement = await page.locator('#app').isVisible();
  console.log('#app element visible:', appElement);

  // Get all text content
  const bodyText = await page.locator('body').textContent();
  console.log('Body text content:', bodyText?.trim() || '(empty)');

  // Check for any elements
  const allElements = await page.locator('*').count();
  console.log('Total elements on page:', allElements);

  // Check console errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('Console error:', msg.text());
    }
  });

  // Wait a bit to catch any delayed errors
  await page.waitForTimeout(1000);

  // Take screenshot
  await page.screenshot({ path: 'e2e/screenshots/debug-state.png', fullPage: true });
});