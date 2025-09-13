#!/usr/bin/env python3
"""
Test the API fix - document generation should now work end-to-end
"""

import asyncio
from datetime import datetime

from playwright.async_api import async_playwright


async def test_api_fix():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, devtools=True)

        context = await browser.new_context()
        page = await context.new_page()

        # Track success
        generation_successful = False
        document_content = None

        # Console logging
        page.on(
            "console",
            lambda msg: (
                print(f"Console {msg.type}: {msg.text}")
                if msg.type == "error" or "Document generated" in msg.text
                else None
            ),
        )

        # Navigate and open modal
        print("📍 Testing Document Generation Fix")
        print("=" * 50)
        await page.goto("http://localhost:5173/dashboard")
        await page.wait_for_timeout(2000)

        print("1️⃣ Opening document generation modal...")
        await page.click("button:has-text('New Document')")
        await page.wait_for_selector("h3:has-text('Generate New Document')")

        # Fill form
        print("2️⃣ Filling form with test data...")
        await page.fill("input#project_name", "Success Test Project")
        await page.fill("input#author", "AJ")
        await page.fill(
            "textarea#description",
            "Testing the fixed API integration. This should now successfully generate a README document using GPT-4.",
        )
        await page.fill("input#version", "1.0.0")
        await page.select_option("select#license", "MIT")

        # Submit
        print("3️⃣ Submitting form...")
        print("   ⏳ This will take 45-60 seconds for AI generation...")
        start_time = datetime.now()

        await page.click("button:has-text('Generate Document')")

        # Wait for completion (max 120 seconds)
        print("\n4️⃣ Waiting for document generation...")
        max_wait = 120
        waited = 0

        while waited < max_wait:
            await page.wait_for_timeout(5000)
            waited += 5
            elapsed = (datetime.now() - start_time).total_seconds()

            # Check for error
            error_element = await page.query_selector(".bg-red-50 h3:has-text('Generation Failed')")
            if error_element:
                error_text = await page.text_content(".bg-red-50 .text-red-700")
                print(f"\n❌ FAILED: {error_text}")
                break

            # Check for success
            success_element = await page.query_selector("text=Document generated successfully")
            if success_element:
                generation_successful = True
                print(f"\n✅ SUCCESS! Document generated in {elapsed:.1f} seconds")

                # Wait a bit for modal to close
                await page.wait_for_timeout(3000)

                # Check if document is displayed
                readme_content = await page.query_selector("pre")
                if readme_content:
                    document_content = await readme_content.text_content()
                    print(f"   📄 Document content retrieved: {len(document_content)} characters")
                break

            # Show progress
            progress_element = await page.query_selector(".bg-blue-50 .text-blue-700")
            if progress_element:
                progress_text = await progress_element.text_content()
                print(f"   {elapsed:.0f}s - {progress_text}")

        # Final results
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS")
        print("=" * 50)

        if generation_successful:
            print("✅ Document Generation: SUCCESSFUL")
            print(f"⏱️ Total Time: {(datetime.now() - start_time).total_seconds():.1f} seconds")
            if document_content:
                print(f"📄 Content Length: {len(document_content)} characters")
                print("\n📝 First 500 characters of generated document:")
                print("-" * 40)
                print(document_content[:500])
                print("-" * 40)
        else:
            print("❌ Document Generation: FAILED")
            print("   Check the error message above for details")

        # Take screenshot
        await page.screenshot(path="test_fix_result.png", full_page=True)
        print("\n📸 Screenshot saved as test_fix_result.png")

        # Summary
        print("\n🎯 SUMMARY")
        if generation_successful:
            print("✅ The API integration fix is WORKING!")
            print("   - Frontend properly sends request")
            print("   - Backend generates document with AI")
            print("   - Response is correctly processed")
            print("   - Document is displayed to user")
        else:
            print("❌ The issue is not fully resolved")
            print("   Further debugging needed")

        print("\n⏳ Browser will remain open for 20 seconds...")
        await asyncio.sleep(20)

        await browser.close()
        print("✅ Test complete")


if __name__ == "__main__":
    asyncio.run(test_api_fix())
