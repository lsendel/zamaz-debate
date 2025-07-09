#!/usr/bin/env python3
"""
Manual Debate Integration Script
Use this to save debates from claude.ai into the Zamaz system
"""

import json
import os
from datetime import datetime
from pathlib import Path
import sys


def create_manual_debate():
    """Interactive script to create a debate from claude.ai results"""

    print("🤖 Zamaz Manual Debate Creator")
    print("==============================")
    print("This tool helps you save debates from claude.ai\n")

    # Get debate details
    question = input("📝 Enter the debate question: ").strip()
    if not question:
        print("❌ Question cannot be empty")
        return

    context = input("📋 Enter context (optional): ").strip()

    print("\n📊 Complexity level:")
    print("1. Simple")
    print("2. Moderate")
    print("3. Complex")
    complexity_choice = input("Choose (1-3) [2]: ").strip() or "2"

    complexity_map = {"1": "simple", "2": "moderate", "3": "complex"}
    complexity = complexity_map.get(complexity_choice, "moderate")

    print("\n🎭 Now paste the debate responses from claude.ai")
    print("(Press Ctrl+D when done)\n")

    print("Claude's position:")
    claude_response = []
    try:
        while True:
            line = input()
            claude_response.append(line)
    except EOFError:
        pass
    claude_text = "\n".join(claude_response)

    print("\n\nGemini's position (or second perspective):")
    gemini_response = []
    try:
        while True:
            line = input()
            gemini_response.append(line)
    except EOFError:
        pass
    gemini_text = "\n".join(gemini_response)

    # Create debate structure
    debate_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    debate = {
        "id": debate_id,
        "question": question,
        "context": context,
        "complexity": complexity,
        "rounds": [{"round": 1, "claude": claude_text, "gemini": gemini_text}],
        "start_time": datetime.now().isoformat(),
        "end_time": datetime.now().isoformat(),
        "final_decision": f"Manual debate: {claude_text[:100]}... | {gemini_text[:100]}...",
        "source": "manual_claude_ai",
    }

    # Save debate
    debates_dir = Path(__file__).parent.parent / "data" / "debates"
    debates_dir.mkdir(parents=True, exist_ok=True)

    filename = debates_dir / f"{debate_id}.json"
    with open(filename, "w") as f:
        json.dump(debate, f, indent=2)

    print(f"\n✅ Debate saved to: {filename}")

    # Also save to cache if caching is enabled
    if os.getenv("USE_CACHED_RESPONSES", "false").lower() == "true":
        cache_dir = Path(__file__).parent.parent / "data" / "ai_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache as both Claude and Gemini responses
        import hashlib

        # Cache Claude response
        claude_prompt = f"Question: {question}\nContext: {context}\n\nProvide a concise, well-reasoned answer."
        claude_key = hashlib.md5(claude_prompt.encode()).hexdigest()[:16]
        claude_cache = cache_dir / f"claude_{claude_key}.json"

        with open(claude_cache, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "model": "claude-opus-4-20250514",
                    "messages": [{"role": "user", "content": claude_prompt}],
                    "response": claude_text,
                },
                f,
            )

        # Cache Gemini response
        gemini_key = hashlib.md5(claude_prompt.encode()).hexdigest()[:16]
        gemini_cache = cache_dir / f"gemini_{gemini_key}.json"

        with open(gemini_cache, "w") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "prompt": claude_prompt, "response": gemini_text}, f)

        print("💾 Responses cached for future use")

    print("\n📊 Summary:")
    print(f"Question: {question}")
    print(f"Complexity: {complexity}")
    print(f"Debate ID: {debate_id}")


if __name__ == "__main__":
    create_manual_debate()
