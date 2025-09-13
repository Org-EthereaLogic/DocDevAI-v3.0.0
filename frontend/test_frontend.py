#!/usr/bin/env python3
"""
Real-time DevDocAI Frontend Testing with Playwright
Testing the Vue 3 + Vite + Tailwind CSS frontend
"""

import asyncio
import json
from playwright.async_api import async_playwright
import os
import time

async def test_devdocai_frontend():
    """Comprehensive frontend testing with real-time observations"""

    async with async_playwright() as p:
        # Launch browser with console logging
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            record_video_dir="screenshots/"
        )

        # Enable console logging
        console_logs = []
        page = await context.new_page()

        def handle_console(msg):
            console_logs.append({
                'type': msg.type,
                'text': msg.text,
                'timestamp': time.time()
            })
            print(f"[CONSOLE {msg.type.upper()}] {msg.text}")

        def handle_page_error(error):
            print(f"[PAGE ERROR] {error}")

        page.on('console', handle_console)
        page.on('pageerror', handle_page_error)

        try:
            print("🚀 Starting DevDocAI Frontend Testing...")

            # Test 1: Initial page load
            print("\n📱 Test 1: Loading DevDocAI Frontend...")
            await page.goto('http://localhost:5174/')
            await page.wait_for_load_state('networkidle')

            # Take initial screenshot
            await page.screenshot(path='screenshots/01_initial_load.png', full_page=True)
            print("✅ Initial page loaded and screenshot captured")

            # Test 2: Check page title and structure
            print("\n🏗️ Test 2: Verifying page structure...")
            title = await page.title()
            print(f"Page title: {title}")

            # Check for key elements
            elements_to_check = [
                'header',
                'nav',
                'main',
                '.dashboard, #app, [data-testid="dashboard"]',
                'button'
            ]

            for selector in elements_to_check:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        print(f"✅ Found element: {selector}")
                    else:
                        print(f"❌ Missing element: {selector}")
                except Exception as e:
                    print(f"⚠️ Error checking {selector}: {e}")

            # Test 3: Navigation and buttons
            print("\n🖱️ Test 3: Testing interactive elements...")

            # Find all buttons
            buttons = await page.query_selector_all('button')
            print(f"Found {len(buttons)} buttons on the page")

            for i, button in enumerate(buttons):
                try:
                    text = await button.inner_text()
                    is_visible = await button.is_visible()
                    is_enabled = await button.is_enabled()
                    print(f"Button {i+1}: '{text}' (visible: {is_visible}, enabled: {is_enabled})")
                except:
                    print(f"Button {i+1}: Could not read properties")

            await page.screenshot(path='screenshots/02_buttons_identified.png', full_page=True)

            # Test 4: Form interactions
            print("\n📝 Test 4: Testing form elements...")

            # Look for form inputs
            inputs = await page.query_selector_all('input, textarea, select')
            print(f"Found {len(inputs)} form inputs")

            for i, input_elem in enumerate(inputs):
                try:
                    tag_name = await input_elem.evaluate('el => el.tagName')
                    input_type = await input_elem.get_attribute('type')
                    placeholder = await input_elem.get_attribute('placeholder')
                    print(f"Input {i+1}: {tag_name} type='{input_type}' placeholder='{placeholder}'")
                except:
                    print(f"Input {i+1}: Could not read properties")

            # Test 5: Try to find document generation workflow
            print("\n📄 Test 5: Looking for document generation workflow...")

            # Look for document generation related elements
            doc_selectors = [
                '[data-testid*="generate"]',
                'button:has-text("Generate")',
                'button:has-text("Create")',
                'button:has-text("New")',
                '.generate-btn',
                '#generate-document',
                '[class*="generate"]'
            ]

            for selector in doc_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        print(f"✅ Found generation element: {selector} - '{text}'")

                        # Try clicking it
                        print(f"🖱️ Attempting to click: {text}")
                        await element.click()
                        await page.wait_for_timeout(2000)
                        await page.screenshot(path=f'screenshots/03_after_click_{i}.png', full_page=True)
                        break
                except Exception as e:
                    print(f"⚠️ Could not interact with {selector}: {e}")

            # Test 6: Test backend integration
            print("\n🔌 Test 6: Testing backend integration...")

            # Check if backend is accessible
            try:
                response = await page.evaluate("""
                    async () => {
                        try {
                            const response = await fetch('http://localhost:8000/api/v1/health');
                            return {
                                status: response.status,
                                ok: response.ok,
                                data: await response.text()
                            };
                        } catch (error) {
                            return { error: error.message };
                        }
                    }
                """)
                print(f"Backend health check: {response}")
            except Exception as e:
                print(f"❌ Backend connection error: {e}")

            # Test 7: Try document generation if possible
            print("\n🧪 Test 7: Attempting document generation...")

            # Look for any text inputs to fill
            text_inputs = await page.query_selector_all('input[type="text"], textarea')
            if text_inputs:
                print(f"Found {len(text_inputs)} text inputs, filling with test data...")
                for i, input_elem in enumerate(text_inputs[:3]):  # Fill first 3 inputs
                    try:
                        await input_elem.fill(f"Test content {i+1}")
                        print(f"✅ Filled input {i+1}")
                    except Exception as e:
                        print(f"❌ Could not fill input {i+1}: {e}")

                await page.screenshot(path='screenshots/04_forms_filled.png', full_page=True)

            # Look for submit/generate buttons
            submit_buttons = await page.query_selector_all('button[type="submit"], button:has-text("Generate"), button:has-text("Submit"), button:has-text("Create")')
            if submit_buttons:
                print(f"Found {len(submit_buttons)} submit buttons")
                for button in submit_buttons:
                    try:
                        text = await button.inner_text()
                        if await button.is_visible() and await button.is_enabled():
                            print(f"🖱️ Clicking submit button: '{text}'")
                            await button.click()
                            await page.wait_for_timeout(3000)  # Wait for response
                            await page.screenshot(path='screenshots/05_after_submit.png', full_page=True)
                            break
                    except Exception as e:
                        print(f"❌ Could not click button: {e}")

            # Test 8: Check for errors and warnings
            print("\n🔍 Test 8: Checking for JavaScript errors...")

            if console_logs:
                error_logs = [log for log in console_logs if log['type'] in ['error', 'warning']]
                if error_logs:
                    print("⚠️ Found console errors/warnings:")
                    for log in error_logs:
                        print(f"  [{log['type'].upper()}] {log['text']}")
                else:
                    print("✅ No console errors or warnings detected")
            else:
                print("ℹ️ No console logs captured")

            # Test 9: Responsive testing
            print("\n📱 Test 9: Testing responsive behavior...")

            # Test mobile viewport
            await page.set_viewport_size({'width': 375, 'height': 667})
            await page.wait_for_timeout(1000)
            await page.screenshot(path='screenshots/06_mobile_view.png', full_page=True)
            print("✅ Mobile viewport screenshot captured")

            # Test tablet viewport
            await page.set_viewport_size({'width': 768, 'height': 1024})
            await page.wait_for_timeout(1000)
            await page.screenshot(path='screenshots/07_tablet_view.png', full_page=True)
            print("✅ Tablet viewport screenshot captured")

            # Return to desktop
            await page.set_viewport_size({'width': 1280, 'height': 720})
            await page.wait_for_timeout(1000)
            await page.screenshot(path='screenshots/08_final_desktop.png', full_page=True)
            print("✅ Desktop viewport screenshot captured")

            # Test 10: Final health check
            print("\n🏁 Test 10: Final application health check...")

            # Check if page is still responsive
            try:
                await page.click('body')
                await page.wait_for_timeout(500)
                print("✅ Page is still responsive")
            except Exception as e:
                print(f"❌ Page responsiveness issue: {e}")

            # Final screenshot
            await page.screenshot(path='screenshots/09_final_state.png', full_page=True)

            print("\n🎉 Frontend testing completed!")
            print(f"📸 Screenshots saved to: screenshots/")
            print(f"📊 Total console logs captured: {len(console_logs)}")

            # Save console logs to file
            with open('screenshots/console_logs.json', 'w') as f:
                json.dump(console_logs, f, indent=2)

            return {
                'success': True,
                'console_logs': len(console_logs),
                'errors': len([log for log in console_logs if log['type'] == 'error']),
                'warnings': len([log for log in console_logs if log['type'] == 'warning'])
            }

        except Exception as e:
            print(f"❌ Testing error: {e}")
            await page.screenshot(path='screenshots/error_state.png', full_page=True)
            return {'success': False, 'error': str(e)}

        finally:
            await browser.close()

if __name__ == "__main__":
    # Create screenshots directory
    os.makedirs('screenshots', exist_ok=True)

    # Run the test
    result = asyncio.run(test_devdocai_frontend())
    print(f"\n📋 Test Results: {result}")