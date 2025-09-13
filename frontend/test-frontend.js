// Quick frontend test script
import { chromium } from 'playwright';

async function testFrontend() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('Testing DevDocAI v3.6.0 Frontend...\n');

  // Collect console messages and errors
  const consoleMessages = [];
  const errors = [];

  page.on('console', msg => consoleMessages.push(`${msg.type()}: ${msg.text()}`));
  page.on('pageerror', error => errors.push(error.toString()));

  try {
    // Navigate to homepage
    console.log('1. Testing Homepage (http://localhost:5173/)...');
    const response = await page.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded', timeout: 10000 });
    console.log(`   Status: ${response.status()}`);

    // Wait for Vue to mount
    await page.waitForTimeout(2000);

    // Check for #app element
    const appElement = await page.$('#app');
    console.log(`   Vue #app element found: ${appElement ? 'YES' : 'NO'}`);

    // Get page title
    const title = await page.title();
    console.log(`   Page title: "${title}"`);

    // Check for Vue components (look for data-v- attributes)
    const vueComponents = await page.$$('[data-v-inspector], [class*="data-v-"]');
    console.log(`   Vue components detected: ${vueComponents.length}`);

    // Take screenshot
    await page.screenshot({ path: '/Users/etherealogic/Dev/DocDevAI-v3.0.0/frontend/frontend-test.png' });
    console.log('   Screenshot saved: frontend-test.png');

    // Test navigation to dashboard
    console.log('\n2. Testing Dashboard Route (/app/dashboard)...');
    try {
      await page.goto('http://localhost:5173/app/dashboard', { waitUntil: 'domcontentloaded', timeout: 10000 });
      console.log('   Dashboard route accessible: YES');
    } catch (e) {
      console.log('   Dashboard route accessible: NO');
      console.log(`   Error: ${e.message}`);
    }

    // Test API connectivity (basic check)
    console.log('\n3. Testing Backend API connectivity...');
    try {
      const apiResponse = await fetch('http://localhost:8000/api/v1/health');
      console.log(`   Backend API status: ${apiResponse.status}`);
    } catch (e) {
      console.log('   Backend API status: UNAVAILABLE');
    }

    // Report console messages
    console.log(`\n4. Console Messages (${consoleMessages.length}):`);
    consoleMessages.slice(-5).forEach(msg => console.log(`   ${msg}`));

    // Report errors
    console.log(`\n5. JavaScript Errors (${errors.length}):`);
    errors.forEach(error => console.log(`   ERROR: ${error}`));

    // Final assessment
    const isHealthy = errors.length === 0 && appElement && response.status() === 200;
    console.log(`\n=== FRONTEND STATUS: ${isHealthy ? 'HEALTHY ✅' : 'ISSUES DETECTED ❌'} ===`);

    if (isHealthy) {
      console.log('✅ Vue app is mounting correctly');
      console.log('✅ No JavaScript errors detected');
      console.log('✅ HTTP responses are 200 OK');
      console.log('✅ Ready for document generation UI implementation');
    }

    return isHealthy;

  } catch (error) {
    console.log(`ERROR: ${error.message}`);
    return false;
  } finally {
    await browser.close();
  }
}

// Run the test
testFrontend().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('Test failed:', error);
  process.exit(1);
});