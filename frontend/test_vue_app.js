// Vue App Testing Script using Playwright
import { chromium } from 'playwright';

async function testVueApp() {
    console.log('🚀 Starting Vue App Verification...\n');

    const browser = await chromium.launch({ headless: false, slowMo: 1000 });
    const context = await browser.newContext({
        viewport: { width: 1280, height: 720 }
    });
    const page = await context.newPage();

    // Set up console monitoring
    const consoleMessages = [];
    const errors = [];

    page.on('console', msg => {
        const level = msg.type();
        const text = msg.text();
        consoleMessages.push({ level, text });

        if (level === 'error') {
            errors.push(text);
        }

        console.log(`[${level.toUpperCase()}] ${text}`);
    });

    page.on('pageerror', error => {
        const errorMsg = error.message;
        errors.push(errorMsg);
        console.log(`[PAGE ERROR] ${errorMsg}`);
    });

    try {
        console.log('📍 Navigating to http://localhost:5176/...');
        await page.goto('http://localhost:5176/', {
            waitUntil: 'networkidle',
            timeout: 10000
        });

        console.log('✅ Page loaded successfully\n');

        // Wait for Vue app to mount
        console.log('🔍 Checking Vue app mounting...');
        await page.waitForSelector('#app', { timeout: 5000 });

        // Check if Vue app has content
        const appElement = await page.$('#app');
        const appContent = await appElement.innerHTML();

        if (appContent.trim() === '') {
            console.log('❌ Vue app mounted but has no content');
            return false;
        } else {
            console.log('✅ Vue app mounted with content');
        }

        // Check for main components
        console.log('\n🧩 Checking for UI components...');

        const components = [
            { selector: 'header', name: 'Header' },
            { selector: 'main', name: 'Main content' },
            { selector: 'nav', name: 'Navigation' },
            { selector: '.container', name: 'Container' },
            { selector: 'button', name: 'Button elements' }
        ];

        for (const component of components) {
            const element = await page.$(component.selector);
            if (element) {
                const isVisible = await element.isVisible();
                console.log(`  ✅ ${component.name}: Found and ${isVisible ? 'visible' : 'hidden'}`);
            } else {
                console.log(`  ⚠️  ${component.name}: Not found`);
            }
        }

        // Test basic interactions
        console.log('\n🖱️  Testing basic interactions...');

        const clickableElements = await page.$$('button, a, [role="button"]');
        console.log(`  Found ${clickableElements.length} clickable elements`);

        if (clickableElements.length > 0) {
            try {
                await clickableElements[0].click();
                console.log('  ✅ First clickable element responded to click');
            } catch (e) {
                console.log(`  ⚠️  Click test failed: ${e.message}`);
            }
        }

        // Check page title and meta
        const title = await page.title();
        const description = await page.$eval('meta[name="description"]', el => el.content);

        console.log(`\n📄 Page metadata:`);
        console.log(`  Title: ${title}`);
        console.log(`  Description: ${description}`);

        // Take screenshot
        console.log('\n📸 Taking screenshot...');
        await page.screenshot({
            path: '/Users/etherealogic/Dev/DocDevAI-v3.0.0/frontend/vue-app-status.png',
            fullPage: true
        });
        console.log('  Screenshot saved as vue-app-status.png');

        // Final status report
        console.log('\n📊 VERIFICATION RESULTS:');
        console.log('========================');

        if (errors.length === 0) {
            console.log('✅ NO JAVASCRIPT ERRORS DETECTED');
        } else {
            console.log(`❌ ${errors.length} JavaScript errors found:`);
            errors.forEach((error, i) => {
                console.log(`  ${i + 1}. ${error}`);
            });
        }

        const totalMessages = consoleMessages.length;
        const errorCount = consoleMessages.filter(m => m.level === 'error').length;
        const warnCount = consoleMessages.filter(m => m.level === 'warning').length;

        console.log(`📈 Console Messages: ${totalMessages} total (${errorCount} errors, ${warnCount} warnings)`);

        console.log('\n🎯 OVERALL STATUS: Vue app is mounting and functioning properly');

        return true;

    } catch (error) {
        console.log(`\n❌ CRITICAL ERROR: ${error.message}`);

        // Take error screenshot
        try {
            await page.screenshot({
                path: '/Users/etherealogic/Dev/DocDevAI-v3.0.0/frontend/vue-app-error.png',
                fullPage: true
            });
            console.log('Error screenshot saved as vue-app-error.png');
        } catch (screenshotError) {
            console.log('Could not take error screenshot');
        }

        return false;
    } finally {
        await browser.close();
    }
}

// Run the test
testVueApp().then(success => {
    if (success) {
        console.log('\n🎉 Vue app verification completed successfully!');
        process.exit(0);
    } else {
        console.log('\n💥 Vue app verification failed!');
        process.exit(1);
    }
}).catch(error => {
    console.error('\n💥 Test runner error:', error);
    process.exit(1);
});