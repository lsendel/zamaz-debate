# self_improve.py
import asyncio
import difflib
import os
import sys
from pathlib import Path

from nucleus import DebateNucleus


async def apply_improvement():
    """Apply an improvement suggested by the nucleus"""

    print("🤖 Self-Improvement Cycle Starting...\n")

    # Load the current nucleus
    nucleus = DebateNucleus()

    # Get improvement suggestion
    improvement = await nucleus.evolve_self()

    print(f"Suggested improvement:\n{improvement['decision']}\n")

    # For v0.1.0, we'll need human approval
    response = input("Apply this improvement? (y/n): ")

    if response.lower() == "y":
        print("\n📝 Please implement the improvement manually.")
        print("Future versions will auto-implement!")
    else:
        print("Improvement skipped.")


async def continuous_improvement():
    """Run continuous improvement loop"""

    while True:
        await apply_improvement()

        # Wait before next improvement
        print("\n⏳ Waiting 1 hour before next improvement...")
        await asyncio.sleep(3600)  # 1 hour


if __name__ == "__main__":
    # Check for API keys
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Please set ANTHROPIC_API_KEY in .env file")
        sys.exit(1)

    # Run single improvement
    asyncio.run(apply_improvement())
