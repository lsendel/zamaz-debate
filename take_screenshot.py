#!/usr/bin/env python3
"""Take a screenshot of the enhanced UI"""

import asyncio
from pyppeteer import launch
import os

async def take_screenshot():
    """Take screenshots of the enhanced UI"""
    
    print("📸 Taking screenshots of the enhanced UI...")
    
    # Launch browser
    browser = await launch(headless=False, args=['--no-sandbox'])
    page = await browser.newPage()
    
    try:
        # Set viewport
        await page.setViewport({'width': 1400, 'height': 900})
        
        # 1. Load main page
        await page.goto('http://localhost:8000')
        await page.waitForSelector('.header', timeout=5000)
        await asyncio.sleep(2)  # Wait for stats to load
        
        # Take dashboard screenshot
        await page.screenshot({'path': 'enhanced_ui_dashboard.png'})
        print("✅ Dashboard screenshot saved as enhanced_ui_dashboard.png")
        
        # 2. Click on New Debate tab
        await page.click('button:nth-child(2)')  # Second button in nav
        await asyncio.sleep(0.5)
        await page.screenshot({'path': 'enhanced_ui_new_debate.png'})
        print("✅ New Debate screenshot saved as enhanced_ui_new_debate.png")
        
        # 3. Click on Debate History tab
        await page.click('button:nth-child(3)')  # Third button in nav
        await asyncio.sleep(1)  # Wait for debates to load
        await page.screenshot({'path': 'enhanced_ui_history.png'})
        print("✅ Debate History screenshot saved as enhanced_ui_history.png")
        
        # 4. Click on Manual Debate tab
        await page.click('button:nth-child(4)')  # Fourth button in nav
        await asyncio.sleep(0.5)
        await page.screenshot({'path': 'enhanced_ui_manual.png'})
        print("✅ Manual Debate screenshot saved as enhanced_ui_manual.png")
        
        # 5. Click on Workflows tab
        await page.click('button:nth-child(5)')  # Fifth button in nav
        await asyncio.sleep(0.5)
        await page.screenshot({'path': 'enhanced_ui_workflows.png'})
        print("✅ Workflows screenshot saved as enhanced_ui_workflows.png")
        
        # 6. Click on Implementations tab
        await page.click('button:nth-child(6)')  # Sixth button in nav
        await asyncio.sleep(0.5)
        await page.screenshot({'path': 'enhanced_ui_implementations.png'})
        print("✅ Implementations screenshot saved as enhanced_ui_implementations.png")
        
        print("\n🎉 All screenshots taken successfully!")
        print("Screenshots are saved in the current directory.")
        
    except Exception as e:
        print(f"\n❌ Error taking screenshots: {str(e)}")
        
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshot())