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
                if response.status >= 400:
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
        print("Navigating to dashboard...")
        await page.goto("http://localhost:5173/dashboard")
        
        # Wait for page to load
        await page.wait_for_timeout(2000)
        
        # Click New Document button
        print("Clicking 'New Document' button...")
        await page.click("button:has-text('New Document')")
        
        # Wait for modal to appear
        await page.wait_for_selector("h3:has-text('Generate New Document')")
        print("Modal opened successfully")
        
        # Fill out the form
        print("Filling out form...")
        await page.fill("input#project_name", "Burger Haven Website")
        await page.fill("input#author", "AJ")
        await page.fill("textarea#description", "A modern, responsive website for Burger Haven restaurant chain. The website serves as the primary digital touchpoint for engaging with customers, showcasing our menu, allowing online ordering, and sharing our brand story.")
        await page.fill("input#version", "1.0.0")
        await page.select_option("select#license", "MIT")
        await page.fill("input#technologies", "React, Node.js, MongoDB, Express")
        await page.fill("input#features", "Online ordering, Menu display, Location finder, Customer reviews")
        
        # Check some README options
        await page.check("input#include_badges")
        await page.check("input#include_toc")
        await page.check("input#include_installation")
        await page.check("input#include_usage")
        
        # Clear previous network logs before submission
        network_requests.clear()
        network_responses.clear()
        console_messages.clear()
        
        # Submit the form
        print("\n=== SUBMITTING FORM ===")
        await page.click("button:has-text('Generate Document')")
        
        # Wait for API call or error (max 10 seconds to see initial response)
        print("Waiting for API response...")
        await page.wait_for_timeout(10000)
        
        # Check for error message
        error_element = await page.query_selector(".bg-red-50 h3:has-text('Generation Failed')")
        if error_element:
            error_text = await page.text_content(".bg-red-50 .text-red-700")
            print(f"\n🔴 ERROR DISPLAYED IN UI: {error_text}")
        
        # Print console messages
        print("\n=== CONSOLE MESSAGES ===")
        for msg in console_messages[-20:]:  # Last 20 messages
            if "API" in msg["text"] or msg["type"] in ["error", "warning"]:
                print(f"{msg['type'].upper()}: {msg['text']}")
        
        # Print network requests
        print("\n=== API REQUESTS ===")
        for req in network_requests:
            if "api" in req["url"].lower() or "documents" in req["url"]:
                print(f"\n{req['method']} {req['url']}")
                print(f"Headers: {json.dumps(req['headers'], indent=2)}")
                if req["post_data"]:
                    try:
                        data = json.loads(req["post_data"])
                        print(f"Request body: {json.dumps(data, indent=2)}")
                    except:
                        print(f"Request body (raw): {req['post_data']}")
        
        # Print network responses
        print("\n=== API RESPONSES ===")
        for res in network_responses:
            if "api" in res["url"].lower() or "documents" in res["url"]:
                print(f"\n{res['status']} {res['url']}")
                if res["body"]:
                    print(f"Response body: {res['body']}")
        
        # Take screenshot of current state
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"debug_screenshot_{timestamp}.png"
        await page.screenshot(path=screenshot_path)
        print(f"\n📸 Screenshot saved as {screenshot_path}")
        
        # Keep browser open for manual inspection
        print("\n⏳ Browser will stay open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)
        
        await browser.close()
        print("✅ Test complete")

# Run the test
asyncio.run(test_document_generation())
