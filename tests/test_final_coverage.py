"""
Final tests to reach 80% coverage
"""
import pytest
import os
from unittest.mock import Mock, patch
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from domain.models import PullRequest
from services.ai_client_factory import AIClientFactory, CachedGeminiClient
from services.delegation_service import DelegationService


class TestFinalCoverage:
    """Tests to reach 80% coverage"""
    
    def test_pr_model_to_github_format(self):
        """Test PullRequest to_github_format method to cover line 114"""
        pr = PullRequest(
            id="pr_test",
            title="Test PR",
            body="Test body",
            branch_name="test-branch",
            base_branch="main",
            assignee="test-user"
        )
        
        # Call to_github_format which should cover line 114
        gh_format = pr.to_github_format()
        
        assert gh_format["title"] == "Test PR"
        assert gh_format["body"] == "Test body"
        assert gh_format["head"] == "test-branch"
        assert gh_format["base"] == "main"
        assert gh_format["assignee"] == "test-user"
        assert "labels" in gh_format
    
    def test_ai_factory_get_gemini_fallback(self):
        """Test get_gemini_client with fallback to cover lines 54, 61"""
        factory = AIClientFactory()
        
        # Mock environment to have GOOGLE_API_KEY
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            # This should create GeminiClientWithFallback
            client = factory.get_gemini_client()
            
            # Verify it has the expected methods
            assert hasattr(client, 'generate_content_async')
    
    def test_ai_factory_mock_mode(self):
        """Test AI factory in mock mode"""
        # Initialize in mock mode (default)
        factory = AIClientFactory()
        
        # Mock mode should return mock clients regardless of API keys
        claude_client = factory.get_claude_client()
        assert hasattr(claude_client, 'create')
        
        gemini_client = factory.get_gemini_client()
        assert hasattr(gemini_client, 'generate_content_async')
    
    def test_web_app_root_no_index(self):
        """Test web app root when index.html doesn't exist"""
        from fastapi.testclient import TestClient
        from src.web.app import app
        
        with TestClient(app) as client:
            # Mock the index file not existing
            with patch('pathlib.Path.exists', return_value=False):
                response = client.get("/")
                
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Welcome to Debate Nucleus API"
    
    def test_evolution_tracker_init(self):
        """Test evolution tracker initialization"""
        from src.core.evolution_tracker import EvolutionTracker
        
        # Mock the file doesn't exist
        with patch('pathlib.Path.exists', return_value=False):
            with patch('pathlib.Path.mkdir'):
                tracker = EvolutionTracker()
                
                # Verify it initializes with empty evolutions
                assert tracker.evolutions == []
                assert tracker.evolution_file is not None
    
    def test_ai_factory_gemini_cached(self):
        """Test getting cached Gemini client to cover line 54"""
        # Set environment for cached mode
        with patch.dict(os.environ, {'USE_CACHED_RESPONSES': 'true', 'USE_MOCK_AI': 'false'}):
            factory = AIClientFactory()
            
            # This should return CachedGeminiClient
            client = factory.get_gemini_client()
            assert isinstance(client, CachedGeminiClient)
    
    def test_ai_factory_gemini_no_key_error(self):
        """Test Gemini client without API key to cover line 61"""
        # Set environment for real API mode
        with patch.dict(os.environ, {'USE_MOCK_AI': 'false', 'USE_CACHED_RESPONSES': 'false'}):
            factory = AIClientFactory()
            
            # Remove GOOGLE_API_KEY if exists
            original_key = os.environ.get('GOOGLE_API_KEY')
            if original_key:
                del os.environ['GOOGLE_API_KEY']
            
            try:
                # This should raise ValueError
                with pytest.raises(ValueError) as exc:
                    factory.get_gemini_client()
                assert "GOOGLE_API_KEY not found" in str(exc.value)
            finally:
                # Restore original key
                if original_key:
                    os.environ['GOOGLE_API_KEY'] = original_key