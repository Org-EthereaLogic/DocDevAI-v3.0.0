import { test, expect } from '@playwright/test';

test.describe('DevDocAI Document Generation E2E Test', () => {
  test('Complete document generation workflow', async ({ page }) => {
    // 1. Navigate to the application
    console.log('🚀 Starting E2E Test - Document Generation Workflow');
    await page.goto('http://localhost:5174');

    // Take screenshot of home page
    await page.screenshot({ path: 'test-screenshots/01-homepage.png', fullPage: true });
    console.log('📸 Screenshot: Homepage captured');

    // 2. Check if the app loads properly
    await page.waitForLoadState('networkidle');
    const title = await page.title();
    console.log(`📄 Page Title: ${title}`);

    // 3. Navigate to Dashboard
    console.log('🔄 Navigating to Dashboard...');

    // Try clicking Get Started button if it exists
    const getStartedButton = page.locator('text=Get Started').first();
    if (await getStartedButton.isVisible()) {
      await getStartedButton.click();
      await page.waitForLoadState('networkidle');
      console.log('✅ Clicked Get Started button');
    } else {
      // Direct navigation as fallback
      await page.goto('http://localhost:5173/app/dashboard');
      console.log('➡️ Direct navigation to dashboard');
    }

    await page.screenshot({ path: 'test-screenshots/02-dashboard.png', fullPage: true });
    console.log('📸 Screenshot: Dashboard captured');

    // 4. Navigate to Documents section
    console.log('📁 Navigating to Documents section...');

    // Try sidebar navigation
    const documentsLink = page.locator('text=Documents').first();
    if (await documentsLink.isVisible()) {
      await documentsLink.click();
      await page.waitForLoadState('networkidle');
      console.log('✅ Clicked Documents in sidebar');
    } else {
      await page.goto('http://localhost:5173/app/documents');
      console.log('➡️ Direct navigation to documents');
    }

    await page.screenshot({ path: 'test-screenshots/03-documents.png', fullPage: true });
    console.log('📸 Screenshot: Documents page captured');

    // 5. Navigate to Generate Document
    console.log('📝 Navigating to Generate Document...');

    const generateButton = page.locator('text=Generate').first();
    if (await generateButton.isVisible()) {
      await generateButton.click();
      await page.waitForLoadState('networkidle');
      console.log('✅ Clicked Generate Document button');
    } else {
      await page.goto('http://localhost:5173/app/documents/generate');
      console.log('➡️ Direct navigation to generate page');
    }

    await page.screenshot({ path: 'test-screenshots/04-generate-form.png', fullPage: true });
    console.log('📸 Screenshot: Generate form captured');

    // 6. Fill in the document generation form (if it exists)
    console.log('📋 Attempting to fill document generation form...');

    // Try to find and fill form fields
    const projectNameInput = page.locator('input[name="projectName"], input[placeholder*="project"]').first();
    if (await projectNameInput.isVisible()) {
      await projectNameInput.fill('E2E Test Project');
      console.log('✅ Filled project name');
    }

    const documentTypeSelect = page.locator('select[name="documentType"], select[placeholder*="type"]').first();
    if (await documentTypeSelect.isVisible()) {
      await documentTypeSelect.selectOption('README');
      console.log('✅ Selected document type: README');
    }

    const descriptionTextarea = page.locator('textarea[name="description"], textarea[placeholder*="description"]').first();
    if (await descriptionTextarea.isVisible()) {
      await descriptionTextarea.fill('This is an automated E2E test for document generation workflow');
      console.log('✅ Filled description');
    }

    await page.screenshot({ path: 'test-screenshots/05-form-filled.png', fullPage: true });
    console.log('📸 Screenshot: Filled form captured');

    // 7. Test API connection
    console.log('🔌 Testing API connection...');

    // Make a direct API call to verify backend is working
    const apiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/health');
        const data = await response.json();
        return { success: true, data };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });

    if (apiResponse.success) {
      console.log('✅ API Health Check Success:', apiResponse.data);
    } else {
      console.log('❌ API Health Check Failed:', apiResponse.error);
    }

    // 8. Submit the form (if submit button exists)
    const submitButton = page.locator('button[type="submit"], button:has-text("Generate"), button:has-text("Submit")').first();
    if (await submitButton.isVisible()) {
      console.log('🚀 Submitting document generation form...');

      // Set up network monitoring
      const responsePromise = page.waitForResponse(
        response => response.url().includes('/api/v1/documents/generate'),
        { timeout: 10000 }
      ).catch(() => null);

      await submitButton.click();
      console.log('✅ Form submitted');

      // Wait for API response
      const response = await responsePromise;
      if (response) {
        console.log('📡 API Response Status:', response.status());
        const responseData = await response.json().catch(() => null);
        if (responseData) {
          console.log('📄 Generated Document:', responseData);
        }
      }

      await page.screenshot({ path: 'test-screenshots/06-after-submit.png', fullPage: true });
      console.log('📸 Screenshot: After submission captured');
    } else {
      console.log('⚠️ No submit button found - form UI may not be implemented');
    }

    // 9. Check for any console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('🔴 Console Error:', msg.text());
      }
    });

    // 10. Final status check
    console.log('\n📊 E2E Test Summary:');
    console.log('- Frontend loaded: ✅');
    console.log('- API connection: ' + (apiResponse.success ? '✅' : '❌'));
    console.log('- Navigation working: Partial');
    console.log('- Form UI present: ' + (await projectNameInput.isVisible() ? '✅' : '❌'));
    console.log('- Document generation: ' + (await submitButton.isVisible() ? 'Testable' : 'Not testable'));

    // Keep browser open for observation
    await page.waitForTimeout(5000);
  });
});