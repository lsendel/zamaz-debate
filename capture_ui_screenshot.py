#!/usr/bin/env python3
"""
Capture screenshots of the Zamaz Debate UI
"""

import asyncio
from playwright.async_api import async_playwright
import os
from datetime import datetime


async def capture_screenshots():
    """Capture screenshots of different UI endpoints"""
    base_url = "http://localhost:8000"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Set viewport size
        await page.set_viewport_size({"width": 1280, "height": 800})

        # Create screenshots directory
        screenshots_dir = "screenshots"
        os.makedirs(screenshots_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Capture the main API docs page
        print("Capturing API documentation page...")
        await page.goto(f"{base_url}/docs")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=f"{screenshots_dir}/api_docs_{timestamp}.png", full_page=True)
        print(f"✓ Saved: {screenshots_dir}/api_docs_{timestamp}.png")

        # 2. Capture the interactive API explorer
        print("Capturing interactive API explorer...")
        await page.goto(f"{base_url}/redoc")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=f"{screenshots_dir}/api_redoc_{timestamp}.png", full_page=True)
        print(f"✓ Saved: {screenshots_dir}/api_redoc_{timestamp}.png")

        # 3. Make an API call and capture the response
        print("Testing decide endpoint...")
        await page.goto(f"{base_url}/docs")
        await page.wait_for_load_state("networkidle")

        # Expand the /decide endpoint
        decide_button = await page.query_selector('button:has-text("/decide")')
        if decide_button:
            await decide_button.click()
            await page.wait_for_timeout(500)

            # Click "Try it out"
            try_button = await page.query_selector('button:has-text("Try it out")')
            if try_button:
                await try_button.click()
                await page.wait_for_timeout(500)

                # Fill in the request body
                request_body = await page.query_selector("textarea.body-param__text")
                if request_body:
                    await request_body.fill(
                        """{
  "question": "Should we add a dashboard to visualize system metrics?",
  "context": "We want better observability of our debate system"
}"""
                    )

                    # Take screenshot before executing
                    await page.screenshot(path=f"{screenshots_dir}/api_try_it_out_{timestamp}.png")
                    print(f"✓ Saved: {screenshots_dir}/api_try_it_out_{timestamp}.png")

        await browser.close()

        print("\n✅ All screenshots captured successfully!")
        print(f"📁 Screenshots saved in: {screenshots_dir}/")


if __name__ == "__main__":
    asyncio.run(capture_screenshots())
