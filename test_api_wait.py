#!/usr/bin/env python3
"""
Test API with proper wait for long-running document generation
"""

import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime

async def test_api_with_wait():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            devtools=True
        )

        context = await browser.new_context()
        page = await context.new_page()

        # Track API response
        api_response_received = False
        api_response_data = None

        async def handle_response(response):
            nonlocal api_response_received, api_response_data
            if "api/v1/documents" in response.url and response.request.method == "POST":
                print(f"\n📥 POST Response received: {response.status} {response.url}")
                api_response_received = True
                try:
                    api_response_data = await response.json()
                    print(f"   Response data received: {len(str(api_response_data))} bytes")
                except:
                    api_response_data = await response.text()
                    print(f"   Response text: {api_response_data[:200]}...")

        page.on("response", handle_response)

        # Console logging
        page.on("console", lambda msg: print(f"Console {msg.type}: {msg.text}") if "API" in msg.text or msg.type == "error" else None)

        # Navigate and open modal
        print("📍 Navigating to dashboard...")
        await page.goto("http://localhost:5173/dashboard")
        await page.wait_for_timeout(2000)

        print("🖱️ Opening document generation modal...")
        await page.click("button:has-text('New Document')")
        await page.wait_for_selector("h3:has-text('Generate New Document')")

        # Fill form
        print("📝 Filling form...")
        await page.fill("input#project_name", "Long Wait Test")
        await page.fill("input#author", "Test User")
        await page.fill("textarea#description", "Testing if we properly wait for the full API response which can take 45-60 seconds")

        # Submit and wait for response
        print("\n🚀 Submitting form...")
        print("⏳ This will take 45-60 seconds for AI generation...")
        start_time = datetime.now()

        await page.click("button:has-text('Generate Document')")

        # Wait for API response or timeout (120 seconds)
        max_wait = 120
        waited = 0
        while not api_response_received and waited < max_wait:
            await page.wait_for_timeout(5000)  # Check every 5 seconds
            waited += 5
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"   Waiting... {elapsed:.0f}s elapsed")

            # Check if error appeared
            error_element = await page.query_selector(".bg-red-50 h3:has-text('Generation Failed')")
            if error_element:
                error_text = await page.text_content(".bg-red-50 .text-red-700")
                print(f"\n🔴 ERROR IN UI: {error_text}")
                break

            # Check if document was generated successfully
            success_element = await page.query_selector("text=Document generated successfully")
            if success_element:
                print(f"\n✅ SUCCESS: Document generated!")
                break

        # Final status
        elapsed_total = (datetime.now() - start_time).total_seconds()
        print(f"\n📊 === FINAL STATUS ===")
        print(f"Total time elapsed: {elapsed_total:.1f} seconds")
        print(f"API Response Received: {api_response_received}")

        if api_response_data:
            if isinstance(api_response_data, dict):
                print(f"Response Success: {api_response_data.get('success', 'Unknown')}")
                if api_response_data.get('success'):
                    print(f"Document Type: {api_response_data.get('document_type', 'Unknown')}")
                    print(f"Content Length: {len(api_response_data.get('content', ''))} characters")
                else:
                    print(f"Error: {api_response_data.get('error', 'Unknown error')}")
            else:
                print(f"Response (text): {api_response_data[:200]}...")

        # Check current UI state
        print("\n🔍 === UI STATE ===")

        # Check for error
        error_element = await page.query_selector(".bg-red-50")
        if error_element:
            error_text = await page.text_content(".bg-red-50")
            print(f"Error displayed: {error_text}")

        # Check for progress
        progress_element = await page.query_selector(".bg-blue-50")
        if progress_element:
            progress_text = await page.text_content(".bg-blue-50")
            print(f"Progress displayed: {progress_text[:100]}...")

        # Check if modal is still open
        modal_element = await page.query_selector("h3:has-text('Generate New Document')")
        print(f"Modal still open: {modal_element is not None}")

        # Take screenshot
        await page.screenshot(path="api_wait_test.png", full_page=True)
        print("\n📸 Screenshot saved as api_wait_test.png")

        print("\n⏳ Keeping browser open for inspection...")
        await asyncio.sleep(30)

        await browser.close()
        print("✅ Test complete")

if __name__ == "__main__":
    asyncio.run(test_api_with_wait())