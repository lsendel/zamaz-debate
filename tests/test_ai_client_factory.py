"""
Comprehensive tests for AI Client Factory
"""
import pytest
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from services.ai_client_factory import (
    AIClientFactory, 
    MockClaudeClient, 
    MockGeminiClient,
    MockOpenAIClient,
    CachedClaudeClient,
    CachedGeminiClient,
    GeminiClientWithFallback
)


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


class TestAIClientFactory:
    """Test suite for AI Client Factory"""
    
    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Setup and cleanup environment for each test"""
        # Save original values
        original_mock = os.environ.get("USE_MOCK_AI")
        original_cache = os.environ.get("USE_CACHED_RESPONSES")
        
        # Set defaults
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
        os.environ["GOOGLE_API_KEY"] = "test-google-key"
        os.environ["OPENAI_API_KEY"] = "test-openai-key"
        os.environ["USE_MOCK_AI"] = "false"
        os.environ["USE_CACHED_RESPONSES"] = "false"
        
        yield
        
        # Restore original values
        if original_mock is not None:
            os.environ["USE_MOCK_AI"] = original_mock
        if original_cache is not None:
            os.environ["USE_CACHED_RESPONSES"] = original_cache
    
    def test_initialization_default(self):
        """Test factory initialization with default settings"""
        factory = AIClientFactory()
        assert factory.use_mock is False
        assert factory.use_cache is False
        assert factory.cache_dir == "ai_cache"
    
    def test_initialization_mock_mode(self):
        """Test factory initialization with mock mode"""
        os.environ["USE_MOCK_AI"] = "true"
        factory = AIClientFactory()
        assert factory.use_mock is True
    
    def test_initialization_cache_mode(self):
        """Test factory initialization with cache mode"""
        os.environ["USE_CACHED_RESPONSES"] = "true"
        factory = AIClientFactory()
        assert factory.use_cache is True
        assert os.path.exists(factory.cache_dir)
    
    def test_get_claude_client_mock(self):
        """Test getting mock Claude client"""
        os.environ["USE_MOCK_AI"] = "true"
        factory = AIClientFactory()
        client = factory.get_claude_client()
        
        assert isinstance(client, MockClaudeClient)
    
    def test_get_claude_client_cached(self, temp_cache_dir):
        """Test getting cached Claude client"""
        os.environ["USE_CACHED_RESPONSES"] = "true"
        factory = AIClientFactory()
        factory.cache_dir = temp_cache_dir
        client = factory.get_claude_client()
        
        assert isinstance(client, CachedClaudeClient)
        assert client.cache_dir == temp_cache_dir
    
    @patch('anthropic.Anthropic')
    def test_get_claude_client_real(self, mock_anthropic_class):
        """Test getting real Claude client"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        factory = AIClientFactory()
        client = factory.get_claude_client()
        
        assert client == mock_client
        mock_anthropic_class.assert_called_once_with(api_key="test-anthropic-key")
    
    def test_get_claude_client_no_api_key(self):
        """Test Claude client without API key"""
        os.environ.pop("ANTHROPIC_API_KEY", None)
        factory = AIClientFactory()
        
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
            factory.get_claude_client()
        
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
    
    def test_get_gemini_client_mock(self):
        """Test getting mock Gemini client"""
        os.environ["USE_MOCK_AI"] = "true"
        factory = AIClientFactory()
        client = factory.get_gemini_client()
        
        assert isinstance(client, MockGeminiClient)
    
    @patch('google.generativeai.configure')
    def test_get_gemini_client_real(self, mock_genai_configure):
        """Test getting real Gemini client with fallback"""
        factory = AIClientFactory()
        client = factory.get_gemini_client()
        
        assert isinstance(client, GeminiClientWithFallback)
        mock_genai_configure.assert_called_once_with(api_key="test-google-key")
    
    def test_get_openai_client_mock(self):
        """Test getting mock OpenAI client"""
        os.environ["USE_MOCK_AI"] = "true"
        factory = AIClientFactory()
        client = factory.get_openai_client()
        
        assert isinstance(client, MockOpenAIClient)


class TestMockClaudeClient:
    """Test suite for MockClaudeClient"""
    
    def test_mock_response_implementation(self):
        """Test mock response for implementation questions"""
        client = MockClaudeClient()
        response = client.messages.create(
            model="test",
            messages=[{"role": "user", "content": "Should we implement this feature?"}],
            max_tokens=100
        )
        
        assert hasattr(response, 'content')
        assert len(response.content) > 0
        assert "implementing" in response.content[0].text.lower() or "beneficial" in response.content[0].text.lower()
    
    def test_mock_response_architecture(self):
        """Test mock response for architecture questions"""
        client = MockClaudeClient()
        response = client.messages.create(
            model="test",
            messages=[{"role": "user", "content": "What architecture should we use?"}],
            max_tokens=100
        )
        
        assert "architectural" in response.content[0].text.lower() or "architecture" in response.content[0].text.lower() or "factors" in response.content[0].text.lower()
    
    def test_mock_response_general(self):
        """Test mock response for general questions"""
        client = MockClaudeClient()
        response = client.messages.create(
            model="test",
            messages=[{"role": "user", "content": "What do you think?"}],
            max_tokens=100
        )
        
        assert "analysis" in response.content[0].text.lower() or "recommend" in response.content[0].text.lower()
    
    def test_messages_property(self):
        """Test messages property returns self"""
        client = MockClaudeClient()
        assert client.messages == client


class TestMockGeminiClient:
    """Test suite for MockGeminiClient"""
    
    @pytest.mark.asyncio
    async def test_mock_response_implementation(self):
        """Test mock response for implementation questions"""
        client = MockGeminiClient()
        response = await client.generate_content_async("How should we implement this?")
        
        assert hasattr(response, 'text')
        assert "implementation" in response.text.lower()
    
    @pytest.mark.asyncio
    async def test_mock_response_architecture(self):
        """Test mock response for architecture questions"""
        client = MockGeminiClient()
        response = await client.generate_content_async("What architecture pattern to use?")
        
        assert "architectural" in response.text.lower() or "modular" in response.text.lower()
    
    @pytest.mark.asyncio
    async def test_mock_response_general(self):
        """Test mock response for general questions"""
        client = MockGeminiClient()
        response = await client.generate_content_async("Analyze this approach")
        
        assert "analysis" in response.text.lower() or "approach" in response.text.lower()


class TestMockOpenAIClient:
    """Test suite for MockOpenAIClient"""
    
    def test_initialization(self):
        """Test MockOpenAIClient initialization"""
        client = MockOpenAIClient()
        assert hasattr(client, 'chat')
        assert hasattr(client.chat, 'completions')
    
    def test_mock_response_complex(self):
        """Test mock response for complex questions"""
        client = MockOpenAIClient()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Analyze this complex system"}],
            max_tokens=100
        )
        
        assert hasattr(response, 'choices')
        assert len(response.choices) > 0
        assert "complex" in response.choices[0].message.content.lower()
    
    def test_mock_response_simple(self):
        """Test mock response for simple questions"""
        client = MockOpenAIClient()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Simple question"}],
            max_tokens=100
        )
        
        assert "gpt" in response.choices[0].message.content.lower() or "efficient" in response.choices[0].message.content.lower()


class TestCachedClaudeClient:
    """Test suite for CachedClaudeClient"""
    
    def test_cache_key_creation(self, temp_cache_dir):
        """Test cache key generation"""
        client = CachedClaudeClient(temp_cache_dir)
        key = client._create_cache_key(
            "claude-3",
            [{"role": "user", "content": "test message"}]
        )
        assert isinstance(key, str)
        assert len(key) == 16  # MD5 hash truncated to 16 chars
    
    def test_cache_miss_calls_api(self, temp_cache_dir):
        """Test that cache miss triggers API call"""
        client = CachedClaudeClient(temp_cache_dir)
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_api_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock(text="API response")]
            mock_api_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_api_client
            
            response = client.create(
                model="claude-3",
                messages=[{"role": "user", "content": "test"}]
            )
            
            assert response.content[0].text == "API response"
            mock_api_client.messages.create.assert_called_once()
    
    def test_cache_hit_avoids_api(self, temp_cache_dir):
        """Test that cache hit avoids API call"""
        client = CachedClaudeClient(temp_cache_dir)
        
        # Create cached response
        cache_data = {
            "response": "Cached response",
            "timestamp": "2024-01-01T00:00:00",
            "model": "claude-3",
            "messages": [{"role": "user", "content": "test"}]
        }
        
        # Get cache key and write cache file
        messages = [{"role": "user", "content": "test"}]
        cache_key = client._create_cache_key("claude-3", messages)
        cache_file = os.path.join(temp_cache_dir, f"claude_{cache_key}.json")
        
        with open(cache_file, "w") as f:
            json.dump(cache_data, f)
        
        # Call should return cached response without calling API
        response = client.create(
            model="claude-3",
            messages=messages
        )
        
        assert response.content[0].text == "Cached response"
    
    def test_messages_property(self, temp_cache_dir):
        """Test messages property returns self"""
        client = CachedClaudeClient(temp_cache_dir)
        assert client.messages == client


class TestCachedGeminiClient:
    """Test suite for CachedGeminiClient"""
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, temp_cache_dir):
        """Test cache hit returns cached response"""
        client = CachedGeminiClient(temp_cache_dir)
        
        # Create cache file
        import hashlib
        prompt = "test prompt"
        cache_key = hashlib.md5(prompt.encode()).hexdigest()[:16]
        cache_file = os.path.join(temp_cache_dir, f"gemini_{cache_key}.json")
        
        cache_data = {
            "response": "Cached Gemini response",
            "timestamp": "2024-01-01T00:00:00",
            "prompt": prompt
        }
        
        with open(cache_file, "w") as f:
            json.dump(cache_data, f)
        
        # Call should return cached response
        response = await client.generate_content_async(prompt)
        assert response.text == "Cached Gemini response"


class TestGeminiClientWithFallback:
    """Test suite for GeminiClientWithFallback"""
    
    @pytest.mark.asyncio
    async def test_successful_gemini_call(self):
        """Test successful Gemini API call"""
        with patch('google.generativeai.configure'):
            client = GeminiClientWithFallback()
            
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = Mock()
                # Create async mock for generate_content_async
                mock_model.generate_content_async = AsyncMock()
                mock_response = Mock()
                mock_response.text = "Gemini response"
                mock_model.generate_content_async.return_value = mock_response
                mock_model_class.return_value = mock_model
                
                # Force client to recreate gemini_client
                client.gemini_client = None
                response = await client.generate_content_async("test prompt")
                assert response.text == "Gemini response"
    
    @pytest.mark.asyncio 
    async def test_fallback_to_openai_on_error(self):
        """Test fallback to OpenAI when Gemini fails"""
        with patch('google.generativeai.configure'):
            client = GeminiClientWithFallback()
            
            # Make Gemini fail
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = Mock()
                # Make generate_content_async raise an exception with quota error
                mock_model.generate_content_async = AsyncMock(side_effect=Exception("Error 429: Resource exhausted (quota)"))
                mock_model_class.return_value = mock_model
                
                # Mock OpenAI
                with patch('openai.OpenAI') as mock_openai_class:
                    mock_openai = Mock()
                    mock_completion = Mock()
                    mock_completion.choices = [Mock(message=Mock(content="OpenAI fallback response"))]
                    mock_openai.chat.completions.create.return_value = mock_completion
                    mock_openai_class.return_value = mock_openai
                    
                    # Force client to recreate gemini_client
                    client.gemini_client = None
                    response = await client.generate_content_async("test prompt", "complex")
                    assert response.text == "OpenAI fallback response"