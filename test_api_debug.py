#!/usr/bin/env python3
"""
Debug script to test document generation API integration
Captures network requests, responses, and console errors
"""

import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime

async def test_document_generation():
    async with async_playwright() as p:
        # Launch browser with dev tools
        browser = await p.chromium.launch(
            headless=False,
            devtools=True
        )

        # Create context with console and request/response logging
        context = await browser.new_context()

        # Create page
        page = await context.new_page()

        # Capture console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append({
            "type": msg.type,
            "text": msg.text
        }))

        # Capture network requests
        network_requests = []
        def log_request(request):
            network_requests.append({
                "url": request.url,
                "method": request.method,
                "headers": dict(request.headers),
                "post_data": request.post_data
            })
        page.on("request", log_request)

        # Capture network responses
        network_responses = []
        async def log_response(response):
            body = None
            try:
                if response.status >= 400 or "api" in response.url.lower():
                    body = await response.text()
            except:
                pass
            network_responses.append({
                "url": response.url,
                "status": response.status,
                "headers": dict(response.headers),
                "body": body
            })
        page.on("response", log_response)

        # Navigate to dashboard
        print("📍 Navigating to dashboard...")
        await page.goto("http://localhost:5173/dashboard")

        # Wait for page to load
        await page.wait_for_timeout(2000)

        # Click New Document button
        print("🖱️ Clicking 'New Document' button...")
        await page.click("button:has-text('New Document')")

        # Wait for modal to appear
        await page.wait_for_selector("h3:has-text('Generate New Document')")
        print("✅ Modal opened successfully")

        # Fill out the form with minimal required fields
        print("📝 Filling out form...")
        await page.fill("input#project_name", "Burger Haven Website")
        await page.fill("input#author", "AJ")
        await page.fill("textarea#description", "A modern, responsive website for Burger Haven restaurant chain. The website serves as the primary digital touchpoint for engaging with customers, showcasing our menu, allowing online ordering, and sharing our brand story.")

        # Optional fields
        await page.fill("input#version", "1.0.0")
        await page.select_option("select#license", "MIT")

        # Clear previous network logs before submission
        network_requests.clear()
        network_responses.clear()
        console_messages.clear()

        # Submit the form
        print("\n🚀 === SUBMITTING FORM ===")
        await page.click("button:has-text('Generate Document')")

        # Wait for API call or error (max 15 seconds to see initial response)
        print("⏳ Waiting for API response...")
        await page.wait_for_timeout(15000)

        # Check for error message
        error_element = await page.query_selector(".bg-red-50 h3:has-text('Generation Failed')")
        error_text = None
        if error_element:
            error_text = await page.text_content(".bg-red-50 .text-red-700")
            print(f"\n🔴 ERROR DISPLAYED IN UI: {error_text}")

        # Check for success or progress
        progress_element = await page.query_selector(".bg-blue-50")
        if progress_element:
            progress_text = await page.text_content(".bg-blue-50")
            print(f"\n🔵 PROGRESS DISPLAYED: {progress_text}")

        # Print console messages
        print("\n📋 === CONSOLE MESSAGES ===")
        api_messages = []
        error_messages = []
        for msg in console_messages:
            if "API" in msg["text"]:
                api_messages.append(msg)
            if msg["type"] in ["error", "warning"]:
                error_messages.append(msg)

        if api_messages:
            print("\nAPI-related messages:")
            for msg in api_messages:
                print(f"  {msg['type']}: {msg['text']}")

        if error_messages:
            print("\nError/Warning messages:")
            for msg in error_messages:
                print(f"  {msg['type']}: {msg['text']}")

        # Print network requests
        print("\n📤 === API REQUESTS ===")
        api_requests = [req for req in network_requests if "api" in req["url"].lower() or "documents" in req["url"]]

        if api_requests:
            for req in api_requests:
                print(f"\n{req['method']} {req['url']}")
                print(f"Content-Type: {req['headers'].get('content-type', 'Not set')}")
                if req["post_data"]:
                    try:
                        data = json.loads(req["post_data"])
                        print(f"Request body:\n{json.dumps(data, indent=2)}")
                    except:
                        print(f"Request body (raw): {req['post_data'][:200]}...")
        else:
            print("❌ NO API REQUESTS FOUND - This is the problem!")

        # Print network responses
        print("\n📥 === API RESPONSES ===")
        api_responses = [res for res in network_responses if "api" in res["url"].lower() or "documents" in res["url"]]

        if api_responses:
            for res in api_responses:
                print(f"\n{res['status']} {res['url']}")
                if res["body"] and res["status"] >= 400:
                    print(f"Error response:\n{res['body'][:500]}...")
        else:
            print("❌ NO API RESPONSES FOUND - API call may not be happening")

        # Check for CORS errors in console
        print("\n🔍 === DIAGNOSTICS ===")
        cors_errors = [msg for msg in console_messages if "CORS" in msg["text"] or "cross-origin" in msg["text"].lower()]
        if cors_errors:
            print("⚠️ CORS ERRORS DETECTED:")
            for msg in cors_errors:
                print(f"  {msg['text']}")

        network_errors = [msg for msg in console_messages if "network" in msg["text"].lower() or "ERR_" in msg["text"]]
        if network_errors:
            print("⚠️ NETWORK ERRORS DETECTED:")
            for msg in network_errors:
                print(f"  {msg['text']}")

        # Take screenshot of current state
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"debug_api_{timestamp}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n📸 Screenshot saved as {screenshot_path}")

        # Summary
        print("\n📊 === SUMMARY ===")
        print(f"API Requests Made: {len(api_requests)}")
        print(f"API Responses Received: {len(api_responses)}")
        print(f"Console Errors: {len(error_messages)}")
        print(f"UI Error Displayed: {'Yes - ' + (error_text or 'Unknown error') if error_element else 'No'}")

        # Keep browser open for manual inspection
        print("\n⏳ Browser will stay open for 30 seconds for manual inspection...")
        print("   Open DevTools Network tab to see more details")
        await asyncio.sleep(30)

        await browser.close()
        print("✅ Test complete")

if __name__ == "__main__":
    asyncio.run(test_document_generation())