#!/usr/bin/env python3
"""Test the professional UI navigation with Puppeteer"""

import asyncio
import os
from pyppeteer import launch
from datetime import datetime

async def test_professional_ui():
    """Test all aspects of the professional UI"""
    
    print("🚀 Testing Professional UI Navigation...")
    print("=" * 50)
    
    # Launch browser
    browser = await launch(
        headless=False,  # Set to True for CI/CD
        args=['--no-sandbox', '--disable-setuid-sandbox'],
        defaultViewport={'width': 1400, 'height': 900}
    )
    
    page = await browser.newPage()
    results = []
    
    try:
        # 1. Load the page
        print("📱 Loading professional UI...")
        await page.goto('http://localhost:8000', waitUntil='networkidle2')
        await page.waitForSelector('.top-nav', timeout=10000)
        results.append("✅ Page loaded successfully")
        
        # Take initial screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await page.screenshot({'path': f'professional_ui_dashboard_{timestamp}.png'})
        print("📸 Dashboard screenshot saved")
        
        # 2. Test top navigation elements
        print("\n🧭 Testing top navigation...")
        
        # Check logo
        logo_text = await page.evaluate('''() => {
            const logo = document.querySelector('.logo span');
            return logo ? logo.textContent : null;
        }''')
        if logo_text == "Zamaz Debate":
            results.append("✅ Logo displays correctly")
        else:
            results.append("❌ Logo text incorrect")
        
        # Check search box
        search_exists = await page.evaluate('''() => {
            return document.querySelector('#global-search') !== null;
        }''')
        if search_exists:
            results.append("✅ Global search box present")
        else:
            results.append("❌ Global search box missing")
        
        # Check notification badge
        badge_count = await page.evaluate('''() => {
            const badge = document.querySelector('.notification-badge');
            return badge ? badge.textContent : null;
        }''')
        if badge_count:
            results.append(f"✅ Notification badge shows: {badge_count}")
        else:
            results.append("❌ Notification badge missing")
        
        # 3. Test navigation tabs
        print("\n📑 Testing navigation tabs...")
        tabs = [
            ('new-debate', 'New Debate', 'Start a New Debate'),
            ('history', 'History', 'Debate History'),
            ('manual', 'Manual Entry', 'Manual Debate Entry'),
            ('workflows', 'Workflows', 'Available Workflows'),
            ('implementations', 'Tasks', 'Implementation Tasks')
        ]
        
        for tab_id, tab_name, expected_title in tabs:
            print(f"\n  Testing {tab_name} tab...")
            
            # Click the tab
            await page.evaluate(f'''() => {{
                const tabs = document.querySelectorAll('.nav-tab');
                for (let tab of tabs) {{
                    if (tab.textContent.includes('{tab_name}')) {{
                        tab.click();
                        break;
                    }}
                }}
            }}''')
            
            await asyncio.sleep(0.5)
            
            # Check if content loaded
            content_visible = await page.evaluate(f'''() => {{
                const content = document.getElementById('{tab_id}');
                return content && content.classList.contains('active');
            }}''')
            
            if content_visible:
                results.append(f"✅ {tab_name} tab works")
                
                # Take screenshot
                await page.screenshot({'path': f'professional_ui_{tab_id}_{timestamp}.png'})
                print(f"  📸 {tab_name} screenshot saved")
            else:
                results.append(f"❌ {tab_name} tab failed to load")
        
        # 4. Test Quick Actions
        print("\n⚡ Testing quick actions...")
        
        # Test Quick Debate button
        quick_debate_exists = await page.evaluate('''() => {
            const btn = Array.from(document.querySelectorAll('.action-btn')).find(
                b => b.textContent.includes('Quick Debate')
            );
            return btn !== null;
        }''')
        
        if quick_debate_exists:
            results.append("✅ Quick Debate button present")
        else:
            results.append("❌ Quick Debate button missing")
        
        # Test Evolve button
        evolve_exists = await page.evaluate('''() => {
            const btn = Array.from(document.querySelectorAll('.action-btn')).find(
                b => b.textContent.includes('Evolve')
            );
            return btn !== null;
        }''')
        
        if evolve_exists:
            results.append("✅ Evolve button present")
        else:
            results.append("❌ Evolve button missing")
        
        # 5. Test mobile responsiveness
        print("\n📱 Testing mobile responsiveness...")
        
        # Set mobile viewport
        await page.setViewport({'width': 375, 'height': 667})
        await asyncio.sleep(0.5)
        
        # Check if hamburger menu is visible
        hamburger_visible = await page.evaluate('''() => {
            const btn = document.querySelector('.mobile-menu-btn');
            return btn && window.getComputedStyle(btn).display !== 'none';
        }''')
        
        if hamburger_visible:
            results.append("✅ Mobile hamburger menu visible")
            
            # Click hamburger menu
            await page.click('.mobile-menu-btn')
            await asyncio.sleep(0.3)
            
            # Check if menu opened
            menu_open = await page.evaluate('''() => {
                const nav = document.getElementById('secondary-nav');
                return nav && nav.classList.contains('open');
            }''')
            
            if menu_open:
                results.append("✅ Mobile menu opens correctly")
                await page.screenshot({'path': f'professional_ui_mobile_{timestamp}.png'})
                print("  📸 Mobile view screenshot saved")
            else:
                results.append("❌ Mobile menu failed to open")
        else:
            results.append("❌ Mobile hamburger menu not visible")
        
        # Reset viewport
        await page.setViewport({'width': 1400, 'height': 900})
        
        # 6. Test form interaction
        print("\n📝 Testing form interaction...")
        
        # Go to New Debate tab
        await page.evaluate('''() => {
            const tabs = document.querySelectorAll('.nav-tab');
            for (let tab of tabs) {
                if (tab.textContent.includes('New Debate')) {
                    tab.click();
                    break;
                }
            }
        }''')
        await asyncio.sleep(0.5)
        
        # Fill in the form
        await page.type('#question', 'Should we adopt a professional UI design?')
        await page.type('#context', 'Testing the new professional navigation system')
        await page.select('#complexity', 'moderate')
        
        # Check if form filled correctly
        question_value = await page.evaluate('() => document.getElementById("question").value')
        if question_value:
            results.append("✅ Form inputs work correctly")
        else:
            results.append("❌ Form inputs not working")
        
        # 7. Test dashboard stats
        print("\n📊 Testing dashboard stats...")
        
        # Go back to dashboard
        await page.evaluate('''() => {
            const tabs = document.querySelectorAll('.nav-tab');
            tabs[0].click();  // First tab is Dashboard
        }''')
        await asyncio.sleep(1)
        
        # Check if stats loaded
        stats_loaded = await page.evaluate('''() => {
            const decisions = document.getElementById('stat-decisions').textContent;
            return decisions && decisions !== '-';
        }''')
        
        if stats_loaded:
            results.append("✅ Dashboard stats loaded")
        else:
            results.append("❌ Dashboard stats failed to load")
        
        # 8. Test search functionality
        print("\n🔍 Testing search functionality...")
        
        # Type in global search
        await page.type('#global-search', 'test search')
        
        # Press Enter
        await page.keyboard.press('Enter')
        await asyncio.sleep(0.5)
        
        # Check if it switched to history tab
        history_active = await page.evaluate('''() => {
            const historyTab = document.getElementById('history');
            return historyTab && historyTab.classList.contains('active');
        }''')
        
        if history_active:
            results.append("✅ Global search redirects to history")
        else:
            results.append("❌ Global search not working")
        
    except Exception as e:
        results.append(f"❌ Error during testing: {str(e)}")
        print(f"\n❌ Error: {e}")
    
    finally:
        # Summary
        print("\n" + "=" * 50)
        print("📋 TEST RESULTS SUMMARY:")
        print("=" * 50)
        
        passed = sum(1 for r in results if r.startswith("✅"))
        failed = sum(1 for r in results if r.startswith("❌"))
        
        for result in results:
            print(result)
        
        print("\n" + "=" * 50)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            print("\n🎉 All tests passed! Professional UI is working perfectly!")
        else:
            print("\n⚠️  Some tests failed. Please check the results above.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_professional_ui())