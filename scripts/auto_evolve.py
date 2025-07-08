#!/usr/bin/env python3
"""
Auto Evolution Script for Zamaz Debate System
Automatically triggers system evolution at regular intervals using Playwright
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AutoEvolver:
    def __init__(self):
        # Configuration from environment
        self.base_url = os.getenv("AUTO_EVOLVE_URL", "http://localhost:8000")
        self.interval = self._parse_interval(os.getenv("AUTO_EVOLVE_INTERVAL", "30m"))
        self.enabled = os.getenv("AUTO_EVOLVE_ENABLED", "false").lower() == "true"
        
        # Stats
        self.evolution_count = 0
        self.start_time = datetime.now()
        
    def _parse_interval(self, interval_str: str) -> int:
        """Parse interval string (e.g., '30m', '1h', '45s') to seconds"""
        interval_str = interval_str.strip().lower()
        
        if interval_str.endswith('h'):
            return int(interval_str[:-1]) * 3600
        elif interval_str.endswith('m'):
            return int(interval_str[:-1]) * 60
        elif interval_str.endswith('s'):
            return int(interval_str[:-1])
        else:
            # Default to minutes if no suffix
            return int(interval_str) * 60
    
    async def trigger_evolution(self, page):
        """Trigger evolution using Playwright"""
        try:
            # Call the evolve endpoint
            response = await page.request.post(f"{self.base_url}/evolve")
            
            if response.ok:
                data = await response.json()
                self.evolution_count += 1
                
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Evolution #{self.evolution_count} triggered successfully")
                print(f"  Decision: {data.get('decision', 'N/A')[:100]}...")
                print(f"  Complexity: {data.get('complexity', 'N/A')}")
                print(f"  PR Created: {data.get('pr_created', False)}")
                
                if data.get('duplicate_detected'):
                    print("  ⚠️  Duplicate evolution detected - system may be stabilizing")
                
                return True
            else:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Evolution failed: HTTP {response.status}")
                return False
                
        except Exception as e:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error triggering evolution: {e}")
            return False
    
    async def check_system_health(self, page):
        """Check if the system is healthy"""
        try:
            response = await page.request.get(f"{self.base_url}/stats")
            if response.ok:
                stats = await response.json()
                return True, stats
            else:
                return False, None
        except Exception:
            return False, None
    
    async def run(self):
        """Main execution loop"""
        if not self.enabled:
            print("❌ Auto-evolution is disabled. Set AUTO_EVOLVE_ENABLED=true in .env to enable.")
            return
        
        print(f"🚀 Starting Auto Evolution System")
        print(f"  URL: {self.base_url}")
        print(f"  Interval: {self.interval} seconds ({self.interval/60:.1f} minutes)")
        print(f"  Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nPress Ctrl+C to stop\n")
        
        async with async_playwright() as p:
            # Launch browser in headless mode
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Initial health check
                healthy, stats = await self.check_system_health(page)
                if healthy:
                    print(f"✅ System is healthy - Stats: {stats}")
                else:
                    print("❌ System health check failed - is the server running?")
                    return
                
                # Main loop
                while True:
                    # Trigger evolution
                    await self.trigger_evolution(page)
                    
                    # Calculate next run time
                    next_run = datetime.now().timestamp() + self.interval
                    next_run_str = datetime.fromtimestamp(next_run).strftime('%H:%M:%S')
                    
                    print(f"  Next evolution scheduled at: {next_run_str}")
                    print(f"  Total evolutions: {self.evolution_count}")
                    
                    # Wait for the interval
                    await asyncio.sleep(self.interval)
                    
            except KeyboardInterrupt:
                print(f"\n\n🛑 Auto-evolution stopped by user")
                print(f"  Total runtime: {datetime.now() - self.start_time}")
                print(f"  Total evolutions: {self.evolution_count}")
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
            finally:
                await browser.close()

async def main():
    """Entry point"""
    evolver = AutoEvolver()
    await evolver.run()

if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")