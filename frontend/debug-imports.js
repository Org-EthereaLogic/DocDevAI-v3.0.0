import { chromium } from 'playwright';

async function debugImports() {
  console.log('🔍 Debugging Import Chain and Network Requests...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const networkRequests = [];
  const failedRequests = [];

  // Monitor network requests
  page.on('request', request => {
    networkRequests.push({
      url: request.url(),
      method: request.method(),
      resourceType: request.resourceType()
    });
  });

  page.on('requestfailed', request => {
    failedRequests.push({
      url: request.url(),
      failure: request.failure()?.errorText
    });
  });

  // Monitor console for import errors
  page.on('console', msg => {
    if (msg.type() === 'error' || msg.text().includes('import') || msg.text().includes('module')) {
      console.log(`🔴 Console: ${msg.text()}`);
    }
  });

  try {
    console.log('Loading page...');
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 15000 });

    console.log('\n📊 Network Analysis:');
    console.log(`Total requests: ${networkRequests.length}`);
    console.log(`Failed requests: ${failedRequests.length}`);

    // Check for JS module requests
    const jsModules = networkRequests.filter(req =>
      req.resourceType === 'script' || req.url.includes('.js') || req.url.includes('.ts')
    );
    console.log(`JS module requests: ${jsModules.length}`);

    if (failedRequests.length > 0) {
      console.log('\n❌ Failed Requests:');
      failedRequests.forEach(req => {
        console.log(`  ${req.url} - ${req.failure}`);
      });
    }

    // Check specific service imports
    const serviceRequests = networkRequests.filter(req =>
      req.url.includes('/services/') || req.url.includes('configuration')
    );
    console.log('\n🔧 Service-related requests:');
    serviceRequests.forEach(req => {
      console.log(`  ${req.method} ${req.url}`);
    });

    // Try to evaluate some JS to see what's available
    try {
      const hasWindow = await page.evaluate(() => typeof window !== 'undefined');
      const hasVue = await page.evaluate(() => typeof window.__VUE_APP__ !== 'undefined');

      console.log(`\n🌐 Runtime Check:`);
      console.log(`Window object: ${hasWindow ? 'Available' : 'Missing'}`);
      console.log(`Vue app: ${hasVue ? 'Available' : 'Missing'}`);

      // Check if we can import the service manually
      const canImportServices = await page.evaluate(async () => {
        try {
          // Try to access the service that's failing
          const module = await import('/src/services/index.ts');
          return {
            success: true,
            hasConfigurationService: !!module.configurationService,
            exports: Object.keys(module)
          };
        } catch (error) {
          return {
            success: false,
            error: error.message
          };
        }
      });

      console.log(`\n🔧 Service Import Test:`, canImportServices);

    } catch (evalError) {
      console.log(`❌ Runtime evaluation failed: ${evalError.message}`);
    }

  } catch (error) {
    console.log(`❌ Page load failed: ${error.message}`);
  } finally {
    await browser.close();
  }
}

debugImports().catch(console.error);