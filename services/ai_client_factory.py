"""
AI Client Factory with multiple provider support
Allows switching between API and alternative methods
"""

import os
from typing import Dict, Any
from enum import Enum
import json
from datetime import datetime


class AIProvider(Enum):
    """Available AI providers"""

    ANTHROPIC_API = "anthropic_api"
    GOOGLE_API = "google_api"
    MOCK = "mock"  # For testing without API calls
    CACHE = "cache"  # Use cached responses


class AIClientFactory:
    """Factory for creating AI clients with different providers"""

    def __init__(self):
        self.use_mock = os.getenv("USE_MOCK_AI", "false").lower() == "true"
        self.use_cache = os.getenv("USE_CACHED_RESPONSES", "false").lower() == "true"
        self.cache_dir = "ai_cache"

        if self.use_cache:
            os.makedirs(self.cache_dir, exist_ok=True)

    def get_claude_client(self):
        """Get Claude client based on configuration"""
        if self.use_mock:
            return MockClaudeClient()
        elif self.use_cache:
            return CachedClaudeClient(self.cache_dir)
        else:
            # Use real API
            from anthropic import Anthropic

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
            return Anthropic(api_key=api_key)

    def get_gemini_client(self):
        """Get Gemini client based on configuration"""
        if self.use_mock:
            return MockGeminiClient()
        elif self.use_cache:
            return CachedGeminiClient(self.cache_dir)
        else:
            # Use real API
            import google.generativeai as genai

            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")
            genai.configure(api_key=api_key)
            return genai.GenerativeModel("gemini-2.0-flash-exp")


class MockClaudeClient:
    """Mock Claude client for testing without API calls"""

    @property
    def messages(self):
        """Return self to support chained API"""
        return self

    def create(self, model: str, messages: list, max_tokens: int = 500) -> Dict:
        """Return mock response"""
        question = messages[0]["content"] if messages else "Unknown"

        # Generate contextual mock response based on question
        if "implement" in question.lower():
            response = "Yes, implementing this feature would be beneficial. Here's a structured approach..."
        elif "architecture" in question.lower():
            response = "For architectural decisions, consider these factors: scalability, maintainability, and performance..."
        else:
            response = "Based on the analysis, I recommend proceeding with careful consideration of the trade-offs..."

        return type(
            "MockResponse", (), {"content": [type("Content", (), {"text": response})]}
        )


class MockGeminiClient:
    """Mock Gemini client for testing without API calls"""

    async def generate_content_async(self, prompt: str) -> Any:
        """Return mock response"""
        if "implement" in prompt.lower():
            text = "Implementation approach: Start with a minimal viable solution and iterate based on feedback..."
        elif "architecture" in prompt.lower():
            text = "Architectural recommendation: Use a modular design pattern for better maintainability..."
        else:
            text = "Analysis complete. The recommended approach balances simplicity with functionality..."

        return type("MockResponse", (), {"text": text})


class CachedClaudeClient:
    """Claude client that caches responses"""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.real_client = None

    @property
    def messages(self):
        """Return self to support chained API"""
        return self

    def create(self, model: str, messages: list, max_tokens: int = 500) -> Dict:
        """Check cache first, then call API if needed"""
        # Create cache key from request
        cache_key = self._create_cache_key(model, messages)
        cache_file = os.path.join(self.cache_dir, f"claude_{cache_key}.json")

        # Check if cached response exists
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                cached = json.load(f)
                # Return cached response
                return type(
                    "CachedResponse",
                    (),
                    {"content": [type("Content", (), {"text": cached["response"]})]},
                )

        # No cache, need to call real API
        if not self.real_client:
            from anthropic import Anthropic

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                # Return mock if no API key
                return MockClaudeClient().create(model, messages, max_tokens)
            self.real_client = Anthropic(api_key=api_key)

        # Call real API
        response = self.real_client.messages.create(
            model=model, messages=messages, max_tokens=max_tokens
        )

        # Cache the response
        with open(cache_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "messages": messages,
                    "response": response.content[0].text,
                },
                f,
            )

        return response

    def _create_cache_key(self, model: str, messages: list) -> str:
        """Create a cache key from request parameters"""
        import hashlib

        content = f"{model}:{json.dumps(messages, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


class CachedGeminiClient:
    """Gemini client that caches responses"""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.real_client = None

    async def generate_content_async(self, prompt: str) -> Any:
        """Check cache first, then call API if needed"""
        # Create cache key from prompt
        import hashlib

        cache_key = hashlib.md5(prompt.encode()).hexdigest()[:16]
        cache_file = os.path.join(self.cache_dir, f"gemini_{cache_key}.json")

        # Check if cached response exists
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                cached = json.load(f)
                return type("CachedResponse", (), {"text": cached["response"]})

        # No cache, need to call real API
        if not self.real_client:
            import google.generativeai as genai

            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                # Return mock if no API key
                return await MockGeminiClient().generate_content_async(prompt)
            genai.configure(api_key=api_key)
            self.real_client = genai.GenerativeModel("gemini-2.0-flash-exp")

        # Call real API
        response = await self.real_client.generate_content_async(prompt)

        # Cache the response
        with open(cache_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "prompt": prompt,
                    "response": response.text,
                },
                f,
            )

        return response


# Usage modes configuration
USAGE_MODES = {
    "production": {
        "USE_MOCK_AI": "false",
        "USE_CACHED_RESPONSES": "false",
        "description": "Full API usage",
    },
    "development": {
        "USE_MOCK_AI": "false",
        "USE_CACHED_RESPONSES": "true",
        "description": "Cache responses to minimize API calls",
    },
    "testing": {
        "USE_MOCK_AI": "true",
        "USE_CACHED_RESPONSES": "false",
        "description": "No API calls, mock responses",
    },
    "demo": {
        "USE_MOCK_AI": "false",
        "USE_CACHED_RESPONSES": "true",
        "description": "Use cached responses when available",
    },
}
