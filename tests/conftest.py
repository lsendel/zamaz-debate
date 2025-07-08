"""
Pytest configuration and fixtures for Zamaz Debate System tests
"""
import pytest
import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Set up test environment variables
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["GOOGLE_API_KEY"] = "test-key"
os.environ["CREATE_PR_FOR_DECISIONS"] = "false"
os.environ["USE_MOCK_AI"] = "true"


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_claude_client():
    """Mock Claude AI client"""
    client = Mock()
    response = Mock()
    response.content = [Mock(text="Mock Claude response: I recommend implementing a testing framework.")]
    client.messages.create = Mock(return_value=response)
    return client


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini AI client"""
    client = Mock()
    response = Mock()
    response.text = "Mock Gemini response: I agree, testing is essential."
    client.generate_content = Mock(return_value=response)
    return client


@pytest.fixture
def mock_ai_factory(mock_claude_client, mock_gemini_client):
    """Mock AI client factory"""
    factory = Mock()
    factory.get_claude_client = Mock(return_value=mock_claude_client)
    factory.get_gemini_client = Mock(return_value=mock_gemini_client)
    return factory