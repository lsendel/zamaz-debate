#!/usr/bin/env python3
"""
Auto Evolution Script for Zamaz Debate System
Triggers evolution at regular intervals
"""
import time
import requests
import json
import os
import sys
import signal
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def signal_handler(sig, frame):
    print("\n\n✋ Auto-evolution stopped by user")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def parse_interval(interval_str):
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

def trigger_evolution(base_url):
    """Trigger a single evolution"""
    try:
        print(f"\n🔄 Triggering evolution at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        response = requests.post(f"{base_url}/evolve", timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Evolution completed!")
            print(f"   - Complexity: {result.get('complexity', 'unknown')}")
            print(f"   - Method: {result.get('method', 'unknown')}")
            if result.get('pr_created'):
                print(f"   - PR Branch: {result.get('pr_branch', 'unknown')}")
            return True
        else:
            print(f"❌ Evolution failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running?")
        return False
    except requests.exceptions.Timeout:
        print("❌ Evolution timed out after 120 seconds")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    # Configuration
    base_url = os.getenv("AUTO_EVOLVE_URL", "http://localhost:8000")
    interval = parse_interval(os.getenv("AUTO_EVOLVE_INTERVAL", "30m"))
    enabled = os.getenv("AUTO_EVOLVE_ENABLED", "false").lower() == "true"
    
    if not enabled:
        print("❌ Auto-evolution is disabled. Set AUTO_EVOLVE_ENABLED=true in .env")
        sys.exit(1)
    
    print("🚀 Starting Auto Evolution")
    print(f"   - URL: {base_url}")
    print(f"   - Interval: {interval} seconds ({os.getenv('AUTO_EVOLVE_INTERVAL', '30m')})")
    print("   - Press Ctrl+C to stop")
    print("\n📊 Auto-evolution will:")
    print("   • Monitor the system continuously")
    print("   • Trigger AI debates about improvements")
    print("   • Create PRs for suggested changes")
    print("   • Show progress after each evolution\n")
    
    evolution_count = 0
    start_time = datetime.now()
    
    while True:
        # Trigger evolution
        if trigger_evolution(base_url):
            evolution_count += 1
        
        # Show stats
        runtime = datetime.now() - start_time
        hours = runtime.total_seconds() / 3600
        print(f"\n📊 Stats: {evolution_count} evolutions in {hours:.1f} hours")
        print(f"⏰ Next evolution in {interval} seconds ({os.getenv('AUTO_EVOLVE_INTERVAL', '30m')})")
        print("💡 Press Ctrl+C to stop\n")
        
        # Wait for next interval
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            signal_handler(None, None)

if __name__ == "__main__":
    main()