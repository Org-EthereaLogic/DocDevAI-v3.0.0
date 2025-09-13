import { test, expect } from '@playwright/test';

test('Quick Frontend and API Check', async ({ page }) => {
  // Check frontend is running
  await page.goto('http://localhost:5174');
  await expect(page).toHaveTitle(/DevDocAI/);
  console.log('✓ Frontend is accessible');

  // Check API through proxy
  const apiResponse = await page.request.get('http://localhost:5174/api/v1/health');
  expect(apiResponse.ok()).toBeTruthy();
  const apiData = await apiResponse.json();
  console.log('✓ API Proxy working:', apiData);

  // Take screenshot of current state
  await page.screenshot({ path: 'e2e/screenshots/current-state.png', fullPage: true });

  // Check for main components
  const mainContent = await page.locator('main').isVisible();
  console.log('✓ Main content area exists:', mainContent);

  // Check for any buttons or interactive elements
  const buttons = await page.locator('button').count();
  console.log(`✓ Found ${buttons} buttons on page`);

  // Check current URL structure
  console.log('✓ Current URL:', page.url());
});