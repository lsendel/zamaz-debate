#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, "scripts")

# Test the configuration
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("AUTO_EVOLVE_URL", "http://localhost:8000")
interval = os.getenv("AUTO_EVOLVE_INTERVAL", "30m")
enabled = os.getenv("AUTO_EVOLVE_ENABLED", "false").lower() == "true"

print(f"Auto-evolve configuration:")
print(f"  Enabled: {enabled}")
print(f"  URL: {base_url}")
print(f"  Interval: {interval}")

if enabled:
    print("\n✅ Auto-evolve is properly configured!")
    print("\nTo run auto-evolve:")
    print("  make auto-evolve")
    print("\nNote: This will run continuously. Press Ctrl+C to stop.")
else:
    print("\n❌ Auto-evolve is disabled")
    print("To enable: make configure-auto-evolve")
