#!/usr/bin/env python3
"""
Check localhost with Puppeteer to capture screenshots and validate UI
"""

import asyncio
import os
import sys
from datetime import datetime
from pyppeteer import launch
import json

async def check_localhost(url="http://localhost:8000"):
    """Check localhost and capture information"""
    
    # Create output directory
    output_dir = "localhost_checks"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"Checking {url}...")
    
    # Launch browser
    browser = await launch(headless=True)
    page = await browser.newPage()
    
    try:
        # Navigate to page
        response = await page.goto(url, {'waitUntil': 'networkidle0'})
        
        # Get status
        status = response.status
        print(f"Status: {status}")
        
        # Take screenshot
        screenshot_path = f"{output_dir}/screenshot_{timestamp}.png"
        await page.screenshot({'path': screenshot_path, 'fullPage': True})
        print(f"Screenshot saved: {screenshot_path}")
        
        # Get page title
        title = await page.title()
        print(f"Title: {title}")
        
        # Get page content
        content = await page.content()
        content_path = f"{output_dir}/content_{timestamp}.html"
        with open(content_path, 'w') as f:
            f.write(content)
        print(f"HTML saved: {content_path}")
        
        # Extract text content
        text_content = await page.evaluate('() => document.body.innerText')
        text_path = f"{output_dir}/text_{timestamp}.txt"
        with open(text_path, 'w') as f:
            f.write(text_content)
        print(f"Text saved: {text_path}")
        
        # Check for specific elements
        elements = {
            'form': await page.querySelector('#debate-form'),
            'question_input': await page.querySelector('#question'),
            'context_input': await page.querySelector('#context'),
            'submit_button': await page.querySelector('#submit-btn'),
            'evolve_button': await page.querySelector('#evolve-btn'),
            'stats': await page.querySelector('#stats')
        }
        
        print("\nPage Elements:")
        for name, element in elements.items():
            exists = element is not None
            print(f"  {name}: {'✓' if exists else '✗'}")
        
        # Try to get stats
        try:
            stats_response = await page.goto(f"{url}/stats", {'waitUntil': 'networkidle0'})
            stats_data = await stats_response.json()
            print(f"\nStats: {json.dumps(stats_data, indent=2)}")
        except Exception as e:
            print(f"\nCouldn't fetch stats: {e}")
        
        # Check for errors on page
        errors = await page.evaluate('''() => {
            const errorElements = document.querySelectorAll('.error, .alert, [class*="error"]');
            return Array.from(errorElements).map(el => el.innerText);
        }''')
        
        if errors:
            print(f"\nErrors found on page:")
            for error in errors:
                print(f"  - {error}")
        
        print(f"\n✓ Check complete. Results saved in {output_dir}/")
        
    except Exception as e:
        print(f"\n✗ Error checking {url}: {e}")
        
    finally:
        await browser.close()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    asyncio.run(check_localhost(url))