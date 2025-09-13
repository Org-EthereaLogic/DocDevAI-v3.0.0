// Browser Console Test Script using Playwright
import { chromium } from 'playwright';

async function testBrowserConsole() {
    console.log('🔍 Checking Browser Console for Errors...\n');

    const browser = await chromium.launch({ headless: false, slowMo: 500 });
    const context = await browser.newContext({
        viewport: { width: 1280, height: 720 }
    });
    const page = await context.newPage();

    // Collect all console messages
    const consoleMessages = [];
    const errors = [];

    page.on('console', msg => {
        const level = msg.type();
        const text = msg.text();
        consoleMessages.push({ level, text, timestamp: new Date() });

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
        console.log('📍 Navigating to Vue app...');
        await page.goto('http://localhost:5176/', {
            waitUntil: 'domcontentloaded',
            timeout: 10000
        });

        console.log('⏳ Waiting 5 seconds for all scripts to load...');
        await page.waitForTimeout(5000);

        // Try to check what's actually in the page
        const pageContent = await page.evaluate(() => {
            return {
                hasApp: !!document.getElementById('app'),
                appContent: document.getElementById('app')?.innerHTML || 'empty',
                appStyle: document.getElementById('app')?.style.cssText || 'no style',
                hasVueScripts: Array.from(document.scripts).some(s => s.src.includes('vue')),
                scriptTags: Array.from(document.scripts).map(s => s.src).filter(src => src),
                documentReady: document.readyState,
                bodyClass: document.body.className,
                headTitle: document.title
            };
        });

        console.log('\n📄 Page Analysis:');
        console.log('================');
        console.log('Document ready state:', pageContent.documentReady);
        console.log('Page title:', pageContent.headTitle);
        console.log('Has #app element:', pageContent.hasApp);
        console.log('App content length:', pageContent.appContent.length, 'characters');
        console.log('App has content:', pageContent.appContent !== 'empty' && pageContent.appContent.trim() !== '');
        console.log('Has Vue scripts:', pageContent.hasVueScripts);
        console.log('Script count:', pageContent.scriptTags.length);

        if (pageContent.appContent.length < 100) {
            console.log('App content preview:', pageContent.appContent);
        }

        // Take screenshot
        await page.screenshot({
            path: '/Users/etherealogic/Dev/DocDevAI-v3.0.0/frontend/browser-console-debug.png',
            fullPage: true
        });

        // Check for specific Vue errors
        const hasVueErrors = errors.some(error =>
            error.includes('vue') ||
            error.includes('Vue') ||
            error.includes('mount') ||
            error.includes('configurationService')
        );

        console.log('\n🚨 Error Summary:');
        console.log('================');
        console.log('Total errors:', errors.length);
        console.log('Vue-related errors:', hasVueErrors);

        if (errors.length > 0) {
            console.log('\nAll errors:');
            errors.forEach((error, i) => {
                console.log(`${i + 1}. ${error}`);
            });
        }

        return {
            success: errors.length === 0 && pageContent.appContent !== 'empty',
            pageAnalysis: pageContent,
            errorCount: errors.length,
            errors: errors
        };

    } catch (error) {
        console.log(`\n❌ BROWSER TEST ERROR: ${error.message}`);
        return { success: false, error: error.message };
    } finally {
        await browser.close();
    }
}

// Run the test
testBrowserConsole().then(result => {
    console.log('\n📊 FINAL RESULT:');
    console.log('===============');

    if (result.success) {
        console.log('✅ Browser test passed - Vue app is working');
    } else {
        console.log('❌ Browser test failed - Issues detected');
        if (result.errorCount > 0) {
            console.log(`💥 ${result.errorCount} errors found`);
        }
    }
}).catch(error => {
    console.error('\n💥 Test runner error:', error);
    process.exit(1);
});