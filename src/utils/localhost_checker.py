#!/usr/bin/env python3
"""
Puppeteer-based localhost validator for Zamaz Debate System
This script captures screenshots and HTML content from localhost URLs
"""

import asyncio
import sys
import os
from datetime import datetime

try:
    from pyppeteer import launch
except ImportError:
    print("Installing pyppeteer...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyppeteer"])
    from pyppeteer import launch

async def check_localhost(url="http://localhost:8000", output_dir="localhost_checks"):
    """
    Check localhost URL and capture screenshot + HTML
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"Launching browser to check {url}...")
    browser = await launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    
    try:
        page = await browser.newPage()
        await page.setViewport({'width': 1920, 'height': 1080})
        
        print(f"Navigating to {url}...")
        response = await page.goto(url, {'waitUntil': 'networkidle0', 'timeout': 30000})
        
        # Capture screenshot
        screenshot_path = os.path.join(output_dir, f"screenshot_{timestamp}.png")
        await page.screenshot({'path': screenshot_path, 'fullPage': True})
        print(f"Screenshot saved: {screenshot_path}")
        
        # Get page content
        content = await page.content()
        html_path = os.path.join(output_dir, f"content_{timestamp}.html")
        with open(html_path, 'w') as f:
            f.write(content)
        print(f"HTML content saved: {html_path}")
        
        # Get page title
        title = await page.title()
        print(f"Page title: {title}")
        
        # Check for specific elements (customize as needed)
        try:
            # Check if debate interface elements exist
            has_debate_form = await page.querySelector('#debate-form') is not None
            has_results = await page.querySelector('#results') is not None
            
            print(f"Debate form present: {has_debate_form}")
            print(f"Results section present: {has_results}")
            
            # Get any visible text content
            text_content = await page.evaluate('() => document.body.innerText')
            text_path = os.path.join(output_dir, f"text_{timestamp}.txt")
            with open(text_path, 'w') as f:
                f.write(text_content)
            print(f"Text content saved: {text_path}")
            
        except Exception as e:
            print(f"Error checking page elements: {e}")
        
        print(f"\nStatus code: {response.status}")
        print(f"Response OK: {response.ok}")
        
    except Exception as e:
            print(f"Error accessing {url}: {e}")
            # Try to capture error screenshot
            try:
                error_screenshot = os.path.join(output_dir, f"error_{timestamp}.png")
                await page.screenshot({'path': error_screenshot})
                print(f"Error screenshot saved: {error_screenshot}")
            except Exception as e2:
                print(f"Could not save error screenshot: {e2}")
    
    finally:
        await browser.close()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    asyncio.run(check_localhost(url))