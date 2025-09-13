import { chromium } from 'playwright';

async function testDirectImport() {
  console.log('🧪 Testing Direct Import of Configuration Service...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Capture all messages
  page.on('console', msg => {
    console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`);
  });

  page.on('pageerror', error => {
    console.log(`❌ Page Error: ${error.toString()}`);
  });

  try {
    // Load the homepage
    await page.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' });

    // Wait a moment for initial load
    await page.waitForTimeout(2000);

    // Test 1: Try importing configuration service directly
    console.log('🔧 Test 1: Direct service import...');
    const test1 = await page.evaluate(async () => {
      try {
        const configModule = await import('/src/services/modules/configuration.ts');
        return {
          success: true,
          hasService: !!configModule.configurationService,
          exports: Object.keys(configModule),
          type: typeof configModule.configurationService
        };
      } catch (error) {
        return {
          success: false,
          error: error.message,
          stack: error.stack
        };
      }
    });
    console.log('Result:', JSON.stringify(test1, null, 2));

    // Test 2: Try importing API client
    console.log('\n🔧 Test 2: API client import...');
    const test2 = await page.evaluate(async () => {
      try {
        const apiModule = await import('/src/services/api.ts');
        return {
          success: true,
          hasClient: !!apiModule.apiClient,
          exports: Object.keys(apiModule),
          clientType: typeof apiModule.apiClient
        };
      } catch (error) {
        return {
          success: false,
          error: error.message
        };
      }
    });
    console.log('Result:', JSON.stringify(test2, null, 2));

    // Test 3: Try importing services index
    console.log('\n🔧 Test 3: Services index import...');
    const test3 = await page.evaluate(async () => {
      try {
        const servicesModule = await import('/src/services/index.ts');
        return {
          success: true,
          exports: Object.keys(servicesModule),
          hasConfigService: !!servicesModule.configurationService
        };
      } catch (error) {
        return {
          success: false,
          error: error.message
        };
      }
    });
    console.log('Result:', JSON.stringify(test3, null, 2));

    // Test 4: Check execution context
    console.log('\n🔧 Test 4: Check execution environment...');
    const test4 = await page.evaluate(() => {
      return {
        hasImportMeta: typeof import.meta !== 'undefined',
        hasEnv: typeof import.meta?.env !== 'undefined',
        isDev: import.meta?.env?.DEV,
        mode: import.meta?.env?.MODE,
        viteEnv: import.meta?.env
      };
    });
    console.log('Environment:', JSON.stringify(test4, null, 2));

  } catch (error) {
    console.log(`❌ Test failed: ${error.message}`);
  } finally {
    await browser.close();
  }
}

testDirectImport().catch(console.error);