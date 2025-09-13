const { chromium } = require('playwright');

async function testActualUserInterface() {
  console.log('🔍 Testing ACTUAL DevDocAI User Interface at http://localhost:5173/\n');

  // Launch browser with visible window
  const browser = await chromium.launch({
    headless: false,  // Show browser window so we can see what happens
    slowMo: 2000      // Slow down to observe UI behavior
  });
  const page = await browser.newPage();

  try {
    console.log('🌐 Navigating to the actual frontend...');
    await page.goto('http://localhost:5173/dashboard');

    // Wait for page to load
    await page.waitForTimeout(3000);

    // Check if page loaded properly
    const title = await page.title();
    console.log(`📄 Page title: ${title}`);

    // Check what's actually rendered on the page
    const bodyContent = await page.$eval('body', el => el.textContent);
    console.log(`📝 Page content preview: ${bodyContent.substring(0, 200)}...`);

    // Check for common UI elements that should exist
    console.log('\n🔎 Looking for expected UI elements...');

    // Check for main app container
    const appElement = await page.$('#app');
    if (appElement) {
      console.log('✅ Found #app element');
    } else {
      console.log('❌ Missing #app element');
    }

    // Check for navigation/header
    const nav = await page.$('nav, header, [role="navigation"]');
    if (nav) {
      console.log('✅ Found navigation element');
      const navText = await nav.textContent();
      console.log(`   Nav content: ${navText.substring(0, 100)}...`);
    } else {
      console.log('❌ Missing navigation element');
    }

    // Check for main content area
    const main = await page.$('main, [role="main"], .main-content');
    if (main) {
      console.log('✅ Found main content area');
    } else {
      console.log('❌ Missing main content area');
    }

    // Check for forms or interactive elements
    const forms = await page.$$('form');
    const buttons = await page.$$('button');
    const inputs = await page.$$('input, select, textarea');

    console.log(`📊 Interactive elements found:`);
    console.log(`   Forms: ${forms.length}`);
    console.log(`   Buttons: ${buttons.length}`);
    console.log(`   Inputs: ${inputs.length}`);

    // Check for any error messages or console errors
    console.log('\n🐛 Checking for errors...');

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        console.log(`❌ Console Error: ${msg.text()}`);
      }
    });

    // Look for error elements on page
    const errorElements = await page.$$('.error, [role="alert"], .alert-error');
    if (errorElements.length > 0) {
      console.log(`⚠️  Found ${errorElements.length} error elements on page`);
      for (const error of errorElements) {
        const errorText = await error.textContent();
        console.log(`   Error: ${errorText}`);
      }
    }

    // Check network requests to see if API calls are working
    console.log('\n🌐 Monitoring network requests...');
    const responses = [];

    page.on('response', (response) => {
      responses.push({
        url: response.url(),
        status: response.status(),
        statusText: response.statusText()
      });
    });

    // Try to interact with the interface if possible
    console.log('\n👆 Attempting to interact with the interface...');

    // Look for generate/submit buttons - specifically the "New Document" button
    const generateButton = await page.$('button:has-text("New Document"), button:has-text("Generate"), button:has-text("Create"), button:has-text("Submit"), input[type="submit"]');
    if (generateButton) {
      console.log('✅ Found action button, attempting to click...');
      try {
        await generateButton.click();
        await page.waitForTimeout(2000);
        console.log('✅ Successfully clicked action button');
      } catch (error) {
        console.log(`❌ Failed to click button: ${error.message}`);
      }
    } else {
      console.log('❌ No actionable buttons found');
    }

    // Check if there are input fields to fill
    const textInputs = await page.$$('input[type="text"], input:not([type]), textarea');
    if (textInputs.length > 0) {
      console.log(`✅ Found ${textInputs.length} text input field(s)`);

      // Try filling the first input
      try {
        await textInputs[0].fill('DevDocAI Test Project');
        console.log('✅ Successfully filled first input field');
      } catch (error) {
        console.log(`❌ Failed to fill input: ${error.message}`);
      }
    }

    // Wait a bit more to see any dynamic behavior
    await page.waitForTimeout(3000);

    // Final network requests summary
    console.log('\n📊 Network Activity Summary:');
    const apiCalls = responses.filter(r => r.url.includes('/api/'));
    const failedRequests = responses.filter(r => r.status >= 400);

    console.log(`   Total requests: ${responses.length}`);
    console.log(`   API calls: ${apiCalls.length}`);
    console.log(`   Failed requests: ${failedRequests.length}`);

    if (failedRequests.length > 0) {
      console.log('   Failed requests:');
      failedRequests.forEach(req => {
        console.log(`     ${req.status} ${req.url}`);
      });
    }

    // Take a screenshot to show current state
    await page.screenshot({ path: 'current-ui-state.png', fullPage: true });
    console.log('📸 Screenshot saved as current-ui-state.png');

    // Keep browser open for observation
    console.log('\n⏱️  Keeping browser open for 10 seconds to observe behavior...');
    await page.waitForTimeout(10000);

    console.log('\n🎯 UI Test Summary:');
    console.log(`   Frontend URL: http://localhost:5173/`);
    console.log(`   Backend URL: http://localhost:8000`);
    console.log(`   Page loaded: ${title ? 'Yes' : 'No'}`);
    console.log(`   Interactive elements: ${forms.length + buttons.length + inputs.length}`);
    console.log(`   Errors detected: ${errorElements.length}`);
    console.log(`   API integration: ${apiCalls.length > 0 ? 'Active' : 'Not detected'}`);

  } catch (error) {
    console.error('❌ UI Test failed:', error);

    // Still take a screenshot to show what went wrong
    try {
      await page.screenshot({ path: 'error-ui-state.png', fullPage: true });
      console.log('📸 Error screenshot saved as error-ui-state.png');
    } catch (screenshotError) {
      console.log('Could not take error screenshot');
    }
  } finally {
    await browser.close();
    console.log('\n🏁 Actual UI test completed!');
  }
}

// Run the test
testActualUserInterface().catch(console.error);
