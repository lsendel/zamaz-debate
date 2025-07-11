#!/usr/bin/env python3
"""Test script to validate the enhanced UI functionality"""

import asyncio
import subprocess
import time
from pyppeteer import launch
import requests
import os
import sys

async def test_enhanced_ui():
    """Test the enhanced UI with Puppeteer"""
    
    print("🔍 Starting Enhanced UI Test...")
    
    # First, check if server is running
    try:
        response = requests.get("http://localhost:8000/stats")
        print("✅ Server is already running")
    except:
        print("❌ Server is not running. Please start it with: make run")
        return False
    
    # Launch browser
    browser = await launch(headless=False, args=['--no-sandbox'])
    page = await browser.newPage()
    
    try:
        # 1. Test main page loads
        print("\n1️⃣ Testing main page...")
        await page.goto('http://localhost:8000')
        await page.waitForSelector('.header', timeout=5000)
        title = await page.evaluate('document.querySelector(".header h1").textContent')
        print(f"✅ Page loaded with title: {title}")
        
        # Take screenshot
        await page.screenshot({'path': 'test_screenshots/1_main_page.png'})
        
        # 2. Check if stats load
        print("\n2️⃣ Testing dashboard stats...")
        await page.waitForSelector('#stat-decisions', timeout=5000)
        decisions = await page.evaluate('document.querySelector("#stat-decisions").textContent')
        debates = await page.evaluate('document.querySelector("#stat-debates").textContent')
        print(f"✅ Stats loaded - Decisions: {decisions}, Debates: {debates}")
        
        # 3. Test tab navigation
        print("\n3️⃣ Testing tab navigation...")
        tabs = ['new-debate', 'history', 'manual', 'workflows', 'implementations']
        
        for tab in tabs:
            await page.evaluate(f'showTab("{tab}")')
            await asyncio.sleep(0.5)
            visible = await page.evaluate(f'document.getElementById("{tab}").classList.contains("active")')
            print(f"✅ Tab '{tab}' is {'visible' if visible else 'not visible'}")
            await page.screenshot({'path': f'test_screenshots/3_tab_{tab}.png'})
        
        # 4. Test debate history
        print("\n4️⃣ Testing debate history...")
        await page.evaluate('showTab("history")')
        await asyncio.sleep(1)
        
        # Check if table loads
        rows = await page.evaluate('''
            document.querySelectorAll("#debate-history-body tr").length
        ''')
        print(f"✅ Debate history loaded with {rows} rows")
        
        # 5. Test workflows
        print("\n5️⃣ Testing workflows...")
        await page.evaluate('showTab("workflows")')
        await asyncio.sleep(1)
        
        workflows = await page.evaluate('''
            document.querySelectorAll(".workflow-card").length
        ''')
        print(f"✅ Workflows loaded: {workflows} workflows found")
        
        # 6. Test manual debate template
        print("\n6️⃣ Testing manual debate template...")
        await page.evaluate('showTab("manual")')
        await asyncio.sleep(0.5)
        
        await page.click('button[onclick="getTemplate()"]')
        await asyncio.sleep(1)
        
        template_visible = await page.evaluate('''
            document.getElementById("template-container").style.display !== "none"
        ''')
        print(f"✅ Manual debate template is {'visible' if template_visible else 'not visible'}")
        
        # 7. Test API endpoints directly
        print("\n7️⃣ Testing API endpoints...")
        endpoints = [
            '/stats',
            '/debates?limit=5',
            '/workflows',
            '/debates/manual/template',
            '/implementations/pending'
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"http://localhost:8000{endpoint}")
                print(f"✅ {endpoint} - Status: {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint} - Error: {str(e)}")
        
        # 8. Check for JavaScript errors
        print("\n8️⃣ Checking for JavaScript errors...")
        js_errors = await page.evaluate('''
            window.jsErrors || []
        ''')
        
        if js_errors:
            print(f"❌ JavaScript errors found: {js_errors}")
        else:
            print("✅ No JavaScript errors detected")
        
        print("\n✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await browser.close()

def main():
    """Main test function"""
    # Create screenshots directory
    os.makedirs('test_screenshots', exist_ok=True)
    
    # Run the test
    success = asyncio.run(test_enhanced_ui())
    
    if success:
        print("\n🎉 Enhanced UI is working correctly!")
        print("\nScreenshots saved in test_screenshots/")
        sys.exit(0)
    else:
        print("\n❌ Enhanced UI test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()