"""
AI Client Factory with multiple provider support
Allows switching between API and alternative methods
"""

import json
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict


class AIProvider(Enum):
    """Available AI providers"""

    ANTHROPIC_API = "anthropic_api"
    GOOGLE_API = "google_api"
    OPENAI_API = "openai_api"
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
            # Use real API with fallback to OpenAI if rate limited
            import google.generativeai as genai

            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")
            genai.configure(api_key=api_key)
            return GeminiClientWithFallback()

    def get_openai_client(self, model="gpt-4o"):
        """Get OpenAI client for fallback"""
        if self.use_mock:
            return MockOpenAIClient()
        elif self.use_cache:
            return CachedOpenAIClient(self.cache_dir, model)
        else:
            from openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            return OpenAI(api_key=api_key)


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

    async def generate_content_async(
        self, prompt: str, complexity: str = "simple"
    ) -> Any:
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


class GeminiClientWithFallback:
    """Gemini client that falls back to OpenAI when rate limited"""

    def __init__(self):
        self.gemini_client = None
        self.openai_fallback = None
        self.use_openai = False

    def generate_content(self, prompt: str, complexity: str = "simple") -> Any:
        """Generate content with fallback to OpenAI

        Args:
            prompt: The prompt to generate content for
            complexity: "simple" or "complex" - determines which GPT model to use
                       complex -> gpt-3.5-turbo
                       simple -> gpt-4o
        """
        if not self.use_openai:
            try:
                if not self.gemini_client:
                    import google.generativeai as genai

                    api_key = os.getenv("GOOGLE_API_KEY")
                    genai.configure(api_key=api_key)
                    self.gemini_client = genai.GenerativeModel("gemini-2.0-flash-exp")

                response = self.gemini_client.generate_content(prompt)
                return response
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    # Determine which model to fall back to
                    model = "gpt-3.5-turbo" if complexity == "complex" else "gpt-4o"
                    print(f"Gemini rate limited, falling back to OpenAI {model}")
                    self.use_openai = True
                else:
                    raise

        # Use OpenAI fallback
        if not self.openai_fallback:
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key or openai_key == "your-openai-api-key-here":
                # Return error message as response
                return type(
                    "ErrorResponse",
                    (),
                    {
                        "text": f"Gemini error: Rate limited. OpenAI API key not configured."
                    },
                )

            from openai import OpenAI

            self.openai_fallback = OpenAI(api_key=openai_key)

        # Determine model based on complexity
        # Per user request: "use 03 for complex systems or 4o for more simple issues"
        model = "gpt-3.5-turbo" if complexity == "complex" else "gpt-4o"

        # Call OpenAI
        try:
            response = self.openai_fallback.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
            )
            # Convert to Gemini-like response format
            return type(
                "OpenAIResponse", (), {"text": response.choices[0].message.content}
            )
        except Exception as e:
            return type(
                "ErrorResponse",
                (),
                {"text": f"Both Gemini and OpenAI failed: {str(e)}"},
            )

    async def generate_content_async(
        self, prompt: str, complexity: str = "simple"
    ) -> Any:
        """Async version of generate_content with fallback to OpenAI

        Args:
            prompt: The prompt to generate content for
            complexity: "simple" or "complex" - determines which GPT model to use
                       complex -> gpt-3.5-turbo
                       simple -> gpt-4o
        """
        if not self.use_openai:
            try:
                if not self.gemini_client:
                    import google.generativeai as genai

                    api_key = os.getenv("GOOGLE_API_KEY")
                    genai.configure(api_key=api_key)
                    self.gemini_client = genai.GenerativeModel("gemini-2.0-flash-exp")

                response = await self.gemini_client.generate_content_async(prompt)
                return response
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    # Determine which model to fall back to
                    model = "gpt-3.5-turbo" if complexity == "complex" else "gpt-4o"
                    print(f"Gemini rate limited, falling back to OpenAI {model}")
                    self.use_openai = True
                else:
                    raise

        # Use OpenAI fallback
        if not self.openai_fallback:
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key or openai_key == "your-openai-api-key-here":
                # Return error message as response
                return type(
                    "ErrorResponse",
                    (),
                    {
                        "text": f"Gemini error: Rate limited. OpenAI API key not configured."
                    },
                )

            from openai import OpenAI

            self.openai_fallback = OpenAI(api_key=openai_key)

        # Determine model based on complexity
        # Per user request: "use 03 for complex systems or 4o for more simple issues"
        model = "gpt-3.5-turbo" if complexity == "complex" else "gpt-4o"

        # Call OpenAI (sync client, no async needed)
        try:
            response = self.openai_fallback.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
            )
            # Convert to Gemini-like response format
            return type(
                "OpenAIResponse", (), {"text": response.choices[0].message.content}
            )
        except Exception as e:
            return type(
                "ErrorResponse",
                (),
                {"text": f"Both Gemini and OpenAI failed: {str(e)}"},
            )


class MockOpenAIClient:
    """Mock OpenAI client for testing"""

    def __init__(self):
        self.chat = type("Chat", (), {"completions": self})()

    def create(self, model: str, messages: list, max_tokens: int = 1000) -> Any:
        """Return mock response"""
        question = messages[-1]["content"] if messages else "Unknown"

        if "complex" in question.lower():
            text = "For complex systems, I recommend using GPT-3.5 for detailed analysis..."
        else:
            text = (
                "For simpler tasks, GPT-4o provides efficient and accurate responses..."
            )

        return type(
            "MockResponse",
            (),
            {
                "choices": [
                    type(
                        "Choice",
                        (),
                        {"message": type("Message", (), {"content": text})},
                    )
                ]
            },
        )


class CachedOpenAIClient:
    """OpenAI client that caches responses"""

    def __init__(self, cache_dir: str, model: str = "gpt-4o"):
        self.cache_dir = cache_dir
        self.model = model
        self.real_client = None
        self.chat = type("Chat", (), {"completions": self})()

    def create(self, model: str, messages: list, max_tokens: int = 1000) -> Any:
        """Check cache first, then call API if needed"""
        import hashlib

        # Create cache key
        content = f"{model}:{json.dumps(messages, sort_keys=True)}"
        cache_key = hashlib.md5(content.encode()).hexdigest()[:16]
        cache_file = os.path.join(self.cache_dir, f"openai_{cache_key}.json")

        # Check cache
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                cached = json.load(f)
                return type(
                    "CachedResponse",
                    (),
                    {
                        "choices": [
                            type(
                                "Choice",
                                (),
                                {
                                    "message": type(
                                        "Message", (), {"content": cached["response"]}
                                    )
                                },
                            )
                        ]
                    },
                )

        # Call real API
        if not self.real_client:
            from openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return MockOpenAIClient().create(model, messages, max_tokens)
            self.real_client = OpenAI(api_key=api_key)

        response = self.real_client.chat.completions.create(
            model=model, messages=messages, max_tokens=max_tokens
        )

        # Cache response
        with open(cache_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "messages": messages,
                    "response": response.choices[0].message.content,
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
