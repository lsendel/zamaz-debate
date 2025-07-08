"""
Tests for Web API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.web.app import app
from domain.models import Decision, DecisionType


class TestWebAPI:
    """Test suite for Web API"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_nucleus(self):
        """Create mock nucleus"""
        nucleus = Mock()
        nucleus.VERSION = "0.1.0"
        nucleus.decision_count = 5
        nucleus.debate_count = 3
        return nucleus
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns HTML"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_stats_endpoint(self, client):
        """Test stats endpoint"""
        with patch('src.web.app.nucleus') as mock_nucleus:
            mock_nucleus.VERSION = "0.1.0"
            mock_nucleus.decision_count = 5
            mock_nucleus.debate_count = 3
            
            response = client.get("/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["version"] == "0.1.0"
            assert data["decisions_made"] == 5
            assert data["debates_run"] == 3
    
    def test_decide_endpoint_simple(self, client):
        """Test decide endpoint with simple decision"""
        with patch('src.web.app.nucleus') as mock_nucleus:
            mock_nucleus.decide = AsyncMock(return_value={
                "decision": "Use blue color",
                "method": "direct",
                "complexity": "simple",
                "rounds": 0,
                "time": "2025-01-01T00:00:00"
            })
            
            response = client.post("/decide", json={
                "question": "What color should we use?",
                "context": "For the logo"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["decision"] == "Use blue color"
            assert data["method"] == "direct"
            assert data["rounds"] == 0
    
    def test_decide_endpoint_complex(self, client):
        """Test decide endpoint with complex decision"""
        with patch('src.web.app.nucleus') as mock_nucleus:
            mock_nucleus.decide = AsyncMock(return_value={
                "decision": "Implement microservices",
                "method": "debate",
                "complexity": "complex",
                "rounds": 1,
                "debate_id": "debate_123",
                "time": "2025-01-01T00:00:00"
            })
            
            response = client.post("/decide", json={
                "question": "Should we migrate to microservices?",
                "context": "Current monolith is slow"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["method"] == "debate"
            assert data["rounds"] == 1
    
    def test_evolve_endpoint(self, client):
        """Test evolve endpoint"""
        with patch('src.web.app.nucleus') as mock_nucleus:
            mock_nucleus.evolve_self = AsyncMock(return_value={
                "decision": "Add testing framework",
                "method": "debate",
                "complexity": "complex",
                "evolution_tracked": True,
                "pr_created": True,
                "pr_branch": "evolution/testing"
            })
            
            response = client.post("/evolve")
            
            assert response.status_code == 200
            data = response.json()
            assert data["evolution_tracked"] is True
            assert data["pr_created"] is True
    
    def test_pr_drafts_endpoint(self, client):
        """Test PR drafts endpoint"""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.glob', return_value=[]):
                response = client.get("/pr-drafts")
                
                assert response.status_code == 200
                data = response.json()
                assert "pr_drafts" in data
                assert isinstance(data["pr_drafts"], list)
    
    def test_decide_missing_params(self, client):
        """Test decide endpoint with missing parameters"""
        response = client.post("/decide", json={})
        assert response.status_code == 422  # Validation error
    
    def test_decide_empty_question(self, client):
        """Test decide endpoint with empty question"""
        response = client.post("/decide", json={
            "question": "",
            "context": "Some context"
        })
        assert response.status_code == 422  # Validation error