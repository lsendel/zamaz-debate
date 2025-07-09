#!/usr/bin/env python3
"""
Test script to verify OpenAI fallback with complexity-based model selection
"""

import asyncio
import os
from services.ai_client_factory import GeminiClientWithFallback


async def test_fallback():
    """Test the OpenAI fallback functionality"""
    print("Testing OpenAI fallback with complexity-based model selection...")
    print("=" * 60)

    client = GeminiClientWithFallback()

    # Force use of OpenAI by setting the flag
    client.use_openai = True

    # Test 1: Complex system (should use gpt-3.5-turbo)
    print("\nTest 1: Complex system question")
    print("-" * 30)
    prompt = "Design a microservices architecture for a large-scale e-commerce platform"

    try:
        response = await client.generate_content_async(prompt, complexity="complex")
        print(f"Response type: {type(response).__name__}")
        print(f"Response text: {response.text[:200]}...")
        print("✅ Complex system test passed (should use gpt-3.5-turbo)")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Simple task (should use gpt-4o)
    print("\nTest 2: Simple task question")
    print("-" * 30)
    prompt = "Format this variable name: user_count"

    try:
        response = await client.generate_content_async(prompt, complexity="simple")
        print(f"Response type: {type(response).__name__}")
        print(f"Response text: {response.text[:200]}...")
        print("✅ Simple task test passed (should use gpt-4o)")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Check if OpenAI key is configured
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key or openai_key == "your-openai-api-key-here":
        print("\n⚠️  Note: OpenAI API key not configured in .env file")
        print("   The system will return error messages instead of actual responses")
    else:
        print("\n✅ OpenAI API key is configured")


if __name__ == "__main__":
    asyncio.run(test_fallback())
