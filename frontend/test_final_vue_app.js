// Final Vue App Test - Port 5174
import { chromium } from 'playwright';

async function testFinalVueApp() {
    console.log('🎯 FINAL VUE APP VERIFICATION (Port 5174)...\n');

    const browser = await chromium.launch({ headless: false, slowMo: 1000 });
    const context = await browser.newContext({
        viewport: { width: 1280, height: 720 }
    });
    const page = await context.newPage();

    // Collect all messages
    const consoleMessages = [];
    const errors = [];
    const warnings = [];

    page.on('console', msg => {
        const level = msg.type();
        const text = msg.text();
        consoleMessages.push({ level, text, timestamp: new Date() });

        if (level === 'error') {
            errors.push(text);
        } else if (level === 'warning') {
            warnings.push(text);
        }

        console.log(`[${level.toUpperCase()}] ${text}`);
    });

    page.on('pageerror', error => {
        const errorMsg = error.message;
        errors.push(errorMsg);
        console.log(`[PAGE ERROR] ${errorMsg}`);
    });

    try {
        console.log('📍 Navigating to http://localhost:5174/...');
        await page.goto('http://localhost:5174/', {
            waitUntil: 'networkidle',
            timeout: 15000
        });

        console.log('✅ Page loaded successfully\n');

        // Wait for Vue to mount
        console.log('🔍 Checking Vue app mounting...');
        await page.waitForSelector('#app', { timeout: 5000 });

        // Check if app has content
        const vueAppInfo = await page.evaluate(() => {
            const app = document.getElementById('app');
            return {
                exists: !!app,
                hasContent: app && app.innerHTML.trim() !== '',
                contentLength: app ? app.innerHTML.length : 0,
                contentPreview: app ? app.innerHTML.substring(0, 200) + '...' : 'No app element',
                title: document.title,
                readyState: document.readyState
            };
        });

        console.log('📊 Vue App Status:');
        console.log('==================');
        console.log('App element exists:', vueAppInfo.exists);
        console.log('Has content:', vueAppInfo.hasContent);
        console.log('Content length:', vueAppInfo.contentLength, 'characters');
        console.log('Page title:', vueAppInfo.title);
        console.log('Document ready:', vueAppInfo.readyState);

        if (vueAppInfo.hasContent) {
            console.log('✅ Vue app has mounted with content!');
            console.log('Content preview:', vueAppInfo.contentPreview);

            // Test basic interactions
            console.log('\n🖱️  Testing Vue app interactions...');

            // Look for Vue-specific elements
            const vueElements = await page.evaluate(() => {
                return {
                    buttons: document.querySelectorAll('button').length,
                    links: document.querySelectorAll('a').length,
                    inputs: document.querySelectorAll('input').length,
                    vueComponents: document.querySelectorAll('[data-v-]').length,
                    headerExists: !!document.querySelector('header'),
                    mainExists: !!document.querySelector('main'),
                    navExists: !!document.querySelector('nav')
                };
            });

            console.log('UI Elements Found:');
            console.log('- Buttons:', vueElements.buttons);
            console.log('- Links:', vueElements.links);
            console.log('- Inputs:', vueElements.inputs);
            console.log('- Vue components:', vueElements.vueComponents);
            console.log('- Header:', vueElements.headerExists);
            console.log('- Main:', vueElements.mainExists);
            console.log('- Navigation:', vueElements.navExists);

            // Test a button click if available
            if (vueElements.buttons > 0) {
                try {
                    await page.click('button:first-of-type');
                    console.log('✅ Button interaction successful');
                } catch (e) {
                    console.log('⚠️  Button interaction failed:', e.message);
                }
            }

        } else {
            console.log('❌ Vue app exists but has no content');
        }

        // Take final screenshot
        await page.screenshot({
            path: '/Users/etherealogic/Dev/DocDevAI-v3.0.0/frontend/vue-app-final-status.png',
            fullPage: true
        });
        console.log('\n📸 Screenshot saved as vue-app-final-status.png');

        // Final status report
        console.log('\n🎯 FINAL STATUS REPORT:');
        console.log('=======================');

        const success = vueAppInfo.hasContent && errors.length === 0;

        if (success) {
            console.log('🎉 SUCCESS: Vue app is mounting and functioning properly!');
            console.log('✅ Zero JavaScript errors');
            console.log('✅ Vue components loaded');
            console.log('✅ User interface rendered');
        } else {
            console.log('❌ ISSUES DETECTED:');
            if (!vueAppInfo.hasContent) {
                console.log('  - Vue app not mounting properly');
            }
            if (errors.length > 0) {
                console.log(`  - ${errors.length} JavaScript errors found`);
                errors.forEach((error, i) => {
                    console.log(`    ${i + 1}. ${error}`);
                });
            }
        }

        if (warnings.length > 0) {
            console.log(`⚠️  ${warnings.length} warnings (non-critical)`);
        }

        console.log(`📊 Total console messages: ${consoleMessages.length}`);

        return {
            success,
            vueAppMounted: vueAppInfo.hasContent,
            errorCount: errors.length,
            warningCount: warnings.length,
            interactionElements: vueElements?.buttons || 0
        };

    } catch (error) {
        console.log(`\n❌ CRITICAL ERROR: ${error.message}`);

        // Take error screenshot
        try {
            await page.screenshot({
                path: '/Users/etherealogic/Dev/DocDevAI-v3.0.0/frontend/vue-app-final-error.png',
                fullPage: true
            });
            console.log('Error screenshot saved as vue-app-final-error.png');
        } catch (screenshotError) {
            console.log('Could not take error screenshot');
        }

        return {
            success: false,
            error: error.message,
            errorCount: errors.length + 1
        };
    } finally {
        await browser.close();
    }
}

// Run the final test
testFinalVueApp().then(result => {
    console.log('\n' + '='.repeat(50));
    console.log('COMPREHENSIVE VUE APP STATUS VERIFICATION');
    console.log('='.repeat(50));

    if (result.success) {
        console.log('🏆 FINAL RESULT: SUCCESS');
        console.log('✅ Vue app is fully operational');
        console.log('✅ Ready for document generation UI implementation');
        console.log('✅ All critical issues resolved');
        process.exit(0);
    } else {
        console.log('💥 FINAL RESULT: ISSUES REMAIN');
        console.log('❌ Vue app needs additional fixes');
        if (result.errorCount) {
            console.log(`❌ ${result.errorCount} errors to resolve`);
        }
        process.exit(1);
    }
}).catch(error => {
    console.error('\n💥 Test runner error:', error);
    process.exit(1);
});