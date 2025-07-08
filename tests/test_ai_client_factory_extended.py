"""
Extended tests for AI Client Factory to improve coverage
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
    CachedClaudeClient,
    CachedGeminiClient
)


class TestAIClientFactoryExtended:
    """Extended tests for AI Client Factory"""
    
    def test_cached_claude_client_cache_miss(self):
        """Test CachedClaudeClient when cache misses"""
        with tempfile.TemporaryDirectory() as temp_dir:
            client = CachedClaudeClient(temp_dir)
            
            # Mock the actual Claude client
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_api = Mock()
                mock_response = Mock()
                mock_response.content = [Mock(text="Claude says hello")]
                mock_api.messages.create.return_value = mock_response
                mock_anthropic.return_value = mock_api
                
                response = client.create(
                    model="claude-3",
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=100
                )
                
                assert response.content[0].text == "Claude says hello"
                
                # Verify cache file was created
                cache_files = list(Path(temp_dir).glob("claude_*.json"))
                assert len(cache_files) == 1
    
    def test_cached_claude_client_valid_cache_different_messages(self):
        """Test CachedClaudeClient with different messages"""
        with tempfile.TemporaryDirectory() as temp_dir:
            client = CachedClaudeClient(temp_dir)
            
            # Mock the actual Claude client
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_api = Mock()
                
                # Different responses for different messages
                response1 = Mock()
                response1.content = [Mock(text="Response 1")]
                response2 = Mock()
                response2.content = [Mock(text="Response 2")]
                
                mock_api.messages.create.side_effect = [response1, response2]
                mock_anthropic.return_value = mock_api
                
                # First call
                resp1 = client.create(
                    model="claude-3",
                    messages=[{"role": "user", "content": "Hello"}]
                )
                assert resp1.content[0].text == "Response 1"
                
                # Second call with different message
                resp2 = client.create(
                    model="claude-3",
                    messages=[{"role": "user", "content": "Goodbye"}]
                )
                assert resp2.content[0].text == "Response 2"
                
                # Both should create cache files
                cache_files = list(Path(temp_dir).glob("claude_*.json"))
                assert len(cache_files) == 2
    
    @pytest.mark.asyncio
    async def test_cached_gemini_client_cache_miss(self):
        """Test CachedGeminiClient when cache misses"""
        with tempfile.TemporaryDirectory() as temp_dir:
            client = CachedGeminiClient(temp_dir)
            
            # Mock the actual Gemini client
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = Mock()
                mock_response = Mock()
                mock_response.text = "Gemini says hello"
                mock_model.generate_content_async = AsyncMock(return_value=mock_response)
                mock_model_class.return_value = mock_model
                
                response = await client.generate_content_async("Hello")
                
                assert response.text == "Gemini says hello"
                
                # Verify cache file was created
                cache_files = list(Path(temp_dir).glob("gemini_*.json"))
                assert len(cache_files) == 1
    
    @pytest.mark.asyncio
    async def test_cached_gemini_client_error_handling(self):
        """Test CachedGeminiClient error handling"""
        with tempfile.TemporaryDirectory() as temp_dir:
            client = CachedGeminiClient(temp_dir)
            
            # Mock Gemini to raise error
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = Mock()
                mock_model.generate_content_async = AsyncMock(
                    side_effect=Exception("API Error")
                )
                mock_model_class.return_value = mock_model
                
                # Should raise the exception since CachedGeminiClient doesn't handle errors
                with pytest.raises(Exception) as exc_info:
                    await client.generate_content_async("Hello")
                
                assert "API Error" in str(exc_info.value)


class TestPRServiceExtended:
    """Extended tests for PR Service"""
    
    @pytest.mark.asyncio
    async def test_add_decision_file(self):
        """Test adding decision file to git"""
        from services.pr_service import PRService
        from domain.models import Decision, DecisionType
        from datetime import datetime
        from unittest.mock import mock_open
        
        service = PRService()
        
        decision = Decision(
            id="test_123",
            question="Test question?",
            context="Test context",
            decision_text="Test decision",
            decision_type=DecisionType.SIMPLE,
            method="direct",
            rounds=0,
            timestamp=datetime.now()
        )
        
        # Mock file operations and subprocess
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('pathlib.Path.mkdir'):
                with patch('builtins.open', mock_open()) as mock_file:
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value = Mock(returncode=0)
                        
                        await service._add_decision_file(decision, "test-branch")
                        
                        # Should have written the decision file
                        mock_file.assert_called()
                        
                        # Should have called git add
                        assert mock_run.called
                        git_add_calls = [call for call in mock_run.call_args_list 
                                       if "git" in str(call) and "add" in str(call)]
                        assert len(git_add_calls) > 0
    
    @pytest.mark.asyncio
    async def test_commit_changes(self):
        """Test committing changes"""
        from services.pr_service import PRService
        from domain.models import PullRequest, Decision, DecisionType
        from datetime import datetime
        
        service = PRService()
        
        pr = PullRequest(
            id="pr_123",
            title="Test PR",
            body="Test body",
            branch_name="test-branch",
            base_branch="main",
            assignee="test-user"
        )
        
        decision = Decision(
            id="test_123",
            question="Test?",
            context="",
            decision_text="Yes",
            decision_type=DecisionType.SIMPLE,
            method="direct",
            rounds=0,
            timestamp=datetime.now()
        )
        
        # Mock subprocess.run
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            await service._commit_changes(pr, decision)
            
            # Should have called git commit
            assert mock_run.called
            commit_calls = [call for call in mock_run.call_args_list
                          if "commit" in str(call[0][0])]
            assert len(commit_calls) > 0