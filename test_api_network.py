#!/usr/bin/env python3
"""
Detailed network debugging for document generation API
Captures full network activity including failed responses
"""

import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime

async def test_api_network():
    async with async_playwright() as p:
        # Launch browser with dev tools
        browser = await p.chromium.launch(
            headless=False,
            devtools=True
        )

        # Create context with detailed network logging
        context = await browser.new_context()

        # Create page with request interception
        page = await context.new_page()

        # Enable CDP (Chrome DevTools Protocol) for more detailed network inspection
        client = await page.context.new_cdp_session(page)
        await client.send("Network.enable")

        # Capture all network activity
        network_log = []

        # Listen for network events via CDP
        async def log_network_event(event_name, params):
            network_log.append({
                "event": event_name,
                "timestamp": datetime.now().isoformat(),
                "params": params
            })

        client.on("Network.requestWillBeSent", lambda params: asyncio.create_task(log_network_event("requestWillBeSent", params)))
        client.on("Network.responseReceived", lambda params: asyncio.create_task(log_network_event("responseReceived", params)))
        client.on("Network.loadingFailed", lambda params: asyncio.create_task(log_network_event("loadingFailed", params)))
        client.on("Network.loadingFinished", lambda params: asyncio.create_task(log_network_event("loadingFinished", params)))

        # Console logging
        console_messages = []
        page.on("console", lambda msg: console_messages.append({
            "type": msg.type,
            "text": msg.text,
            "args": [str(arg) for arg in msg.args]
        }))

        # Page errors
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        # Request failures
        request_failures = []
        page.on("requestfailed", lambda request: request_failures.append({
            "url": request.url,
            "failure": request.failure,
            "method": request.method
        }))

        # Navigate to dashboard
        print("📍 Navigating to dashboard...")
        await page.goto("http://localhost:5173/dashboard")

        # Wait for page to load
        await page.wait_for_timeout(2000)

        # Open Dev Tools Network tab manually
        print("💡 TIP: Open DevTools (F12) and go to Network tab to see real-time activity")

        # Click New Document button
        print("🖱️ Clicking 'New Document' button...")
        await page.click("button:has-text('New Document')")

        # Wait for modal
        await page.wait_for_selector("h3:has-text('Generate New Document')")
        print("✅ Modal opened")

        # Fill form
        print("📝 Filling form...")
        await page.fill("input#project_name", "Network Test Project")
        await page.fill("input#author", "Test User")
        await page.fill("textarea#description", "Testing API network communication to identify where the request fails")

        # Clear logs before submission
        network_log.clear()
        console_messages.clear()
        page_errors.clear()
        request_failures.clear()

        # Submit form
        print("\n🚀 === SUBMITTING FORM ===")
        await page.click("button:has-text('Generate Document')")

        # Wait longer to capture full network activity
        print("⏳ Monitoring network activity for 20 seconds...")
        await page.wait_for_timeout(20000)

        # Analyze network log
        print("\n📊 === NETWORK ANALYSIS ===")

        # Find API requests
        api_requests = [event for event in network_log if event["event"] == "requestWillBeSent" and "api" in event["params"].get("request", {}).get("url", "").lower()]
        api_responses = [event for event in network_log if event["event"] == "responseReceived" and "api" in event["params"].get("response", {}).get("url", "").lower()]
        api_failures = [event for event in network_log if event["event"] == "loadingFailed" and "api" in event["params"].get("requestId", "")]

        print(f"\n📤 API Requests Sent: {len(api_requests)}")
        for req in api_requests:
            request_data = req["params"]["request"]
            print(f"  - {request_data.get('method', 'GET')} {request_data.get('url', 'Unknown')}")
            if request_data.get("postData"):
                try:
                    data = json.loads(request_data["postData"])
                    print(f"    Body: {json.dumps(data, indent=6)[:200]}...")
                except:
                    pass

        print(f"\n📥 API Responses Received: {len(api_responses)}")
        for res in api_responses:
            response_data = res["params"]["response"]
            print(f"  - {response_data.get('status', '???')} {response_data.get('url', 'Unknown')}")
            print(f"    Headers: {response_data.get('headers', {})}")

        print(f"\n❌ API Loading Failures: {len(api_failures)}")
        for fail in api_failures:
            print(f"  - Request ID: {fail['params'].get('requestId', 'Unknown')}")
            print(f"    Error: {fail['params'].get('errorText', 'Unknown error')}")
            print(f"    Type: {fail['params'].get('type', 'Unknown type')}")
            print(f"    Canceled: {fail['params'].get('canceled', False)}")

        # Check request failures
        if request_failures:
            print(f"\n🔴 Request Failures Detected: {len(request_failures)}")
            for failure in request_failures:
                print(f"  - {failure['method']} {failure['url']}")
                print(f"    Failure: {failure['failure']}")

        # Check console errors
        errors = [msg for msg in console_messages if msg["type"] in ["error", "warning"]]
        if errors:
            print(f"\n⚠️ Console Errors/Warnings: {len(errors)}")
            for error in errors[:5]:  # First 5 errors
                print(f"  - {error['type']}: {error['text']}")

        # Check page errors
        if page_errors:
            print(f"\n🔴 Page Errors: {len(page_errors)}")
            for error in page_errors[:5]:
                print(f"  - {error}")

        # Check for CORS issues specifically
        cors_issues = [msg for msg in console_messages if "CORS" in msg["text"] or "cross-origin" in msg["text"].lower()]
        if cors_issues:
            print(f"\n🚫 CORS Issues Detected:")
            for issue in cors_issues:
                print(f"  - {issue['text']}")

        # Check for network errors
        network_errors = [msg for msg in console_messages if "ERR_" in msg["text"] or "network" in msg["text"].lower()]
        if network_errors:
            print(f"\n🌐 Network Errors:")
            for error in network_errors[:5]:
                print(f"  - {error['text']}")

        # Summary
        print("\n📈 === SUMMARY ===")
        print(f"Total Network Events: {len(network_log)}")
        print(f"API Requests: {len(api_requests)}")
        print(f"API Responses: {len(api_responses)}")
        print(f"Request Failures: {len(request_failures)}")
        print(f"Console Errors: {len(errors)}")
        print(f"CORS Issues: {len(cors_issues)}")

        # Diagnosis
        print("\n🔍 === DIAGNOSIS ===")
        if len(api_requests) == 0:
            print("❌ No API requests were sent - Frontend issue")
        elif len(api_responses) == 0:
            print("❌ API requests sent but no responses - Possible CORS or network issue")
            if len(api_failures) > 0:
                print("   - Network failures detected, check error details above")
        elif len(api_responses) > 0:
            print("✅ API is responding - Check response status codes")

        # Take screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"network_debug_{timestamp}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n📸 Screenshot saved as {screenshot_path}")

        print("\n⏳ Keeping browser open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)

        await browser.close()
        print("✅ Test complete")

if __name__ == "__main__":
    asyncio.run(test_api_network())