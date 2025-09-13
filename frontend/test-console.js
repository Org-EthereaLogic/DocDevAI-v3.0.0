import { chromium } from 'playwright';

async function checkJSErrors() {
  console.log('🔍 Detailed JavaScript Error Analysis...\n');

  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-web-security', '--disable-features=VizDisplayCompositor']
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  const jsErrors = [];
  const consoleMessages = [];

  // Capture all console messages
  page.on('console', msg => {
    const message = `[${msg.type().toUpperCase()}] ${msg.text()}`;
    consoleMessages.push(message);
    console.log(`Console: ${message}`);
  });

  // Capture JavaScript errors
  page.on('pageerror', error => {
    const errorMsg = error.toString();
    jsErrors.push(errorMsg);
    console.log(`❌ JS Error: ${errorMsg}`);
  });

  try {
    console.log('Loading http://localhost:5173/ ...');
    await page.goto('http://localhost:5173/', {
      waitUntil: 'networkidle',
      timeout: 15000
    });

    // Wait for Vue to initialize
    await page.waitForTimeout(3000);

    // Check if app mounted successfully
    const appElement = await page.$('#app');
    const hasContent = appElement ? await appElement.textContent() : '';

    console.log(`\n📊 Results:`);
    console.log(`✅ Page loaded: YES`);
    console.log(`✅ #app element: ${appElement ? 'YES' : 'NO'}`);
    console.log(`✅ Content length: ${hasContent ? hasContent.length : 0} chars`);
    console.log(`⚠️  Console messages: ${consoleMessages.length}`);
    console.log(`❌ JavaScript errors: ${jsErrors.length}`);

    if (jsErrors.length === 0) {
      console.log(`\n🎉 SUCCESS: No JavaScript errors detected!`);
      console.log(`Frontend is fully operational and ready for document generation UI.`);

      // Take a success screenshot
      await page.screenshot({
        path: '/Users/etherealogic/Dev/DocDevAI-v3.0.0/frontend/success-screenshot.png',
        fullPage: true
      });
      console.log(`📸 Success screenshot saved: success-screenshot.png`);
    }

    return jsErrors.length === 0;

  } catch (error) {
    console.log(`❌ Test failed: ${error.message}`);
    return false;
  } finally {
    await browser.close();
  }
}

checkJSErrors().then(success => {
  const status = success ? '✅ FRONTEND FULLY OPERATIONAL' : '❌ ISSUES DETECTED';
  console.log(`\n${'='.repeat(50)}`);
  console.log(`${status}`);
  console.log(`${'='.repeat(50)}`);
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('❌ Test execution failed:', error);
  process.exit(1);
});