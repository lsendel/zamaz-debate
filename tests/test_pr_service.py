"""
Tests for PR Service
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent))

from services.pr_service import PRService
from domain.models import Decision, DecisionType, ImplementationAssignee, PullRequest


class TestPRService:
    """Test suite for PRService"""
    
    @pytest.fixture
    def pr_service(self):
        """Create a PRService instance with PR creation disabled"""
        with patch.dict('os.environ', {'CREATE_PR_FOR_DECISIONS': 'false'}):
            return PRService()
    
    @pytest.fixture
    def pr_service_enabled(self):
        """Create a PRService instance with PR creation enabled"""
        with patch.dict('os.environ', {'CREATE_PR_FOR_DECISIONS': 'true'}):
            return PRService()
    
    @pytest.fixture
    def sample_decision(self):
        """Create a sample decision"""
        return Decision(
            id="test_decision_123",
            question="Should we add testing?",
            context="We need better quality",
            decision_text="Yes, implement comprehensive testing",
            decision_type=DecisionType.COMPLEX,
            method="debate",
            rounds=1,
            timestamp=datetime.now()
        )
    
    def test_initialization_disabled(self):
        """Test PR service initialization when disabled"""
        with patch.dict('os.environ', {'CREATE_PR_FOR_DECISIONS': 'false'}, clear=True):
            pr_service = PRService()
            assert pr_service.enabled is False
            assert pr_service.auto_push is False
    
    def test_initialization_enabled(self, pr_service_enabled):
        """Test PR service initialization when enabled"""
        assert pr_service_enabled.enabled is True
    
    def test_should_create_pr_disabled(self, pr_service, sample_decision):
        """Test should_create_pr when service is disabled"""
        assert pr_service.should_create_pr(sample_decision) is False
    
    def test_should_create_pr_complex_decision(self, pr_service_enabled, sample_decision):
        """Test should_create_pr for complex decision"""
        assert pr_service_enabled.should_create_pr(sample_decision) is True
    
    def test_should_create_pr_simple_decision(self, pr_service_enabled):
        """Test should_create_pr for simple decision"""
        simple_decision = Decision(
            id="simple_123",
            question="What color?",
            context="Choose a color",
            decision_text="Blue",
            decision_type=DecisionType.SIMPLE,
            method="direct",
            rounds=0,
            timestamp=datetime.now()
        )
        assert pr_service_enabled.should_create_pr(simple_decision) is False
    
    def test_should_create_pr_evolution(self, pr_service_enabled):
        """Test should_create_pr for evolution decision"""
        evolution_decision = Decision(
            id="evolution_123",
            question="What to improve?",
            context="System evolution",
            decision_text="Add testing",
            decision_type=DecisionType.EVOLUTION,
            method="debate",
            rounds=1,
            timestamp=datetime.now(),
            implementation_assignee=ImplementationAssignee.CLAUDE
        )
        assert pr_service_enabled.should_create_pr(evolution_decision) is True
    
    def test_generate_pr_title(self, pr_service_enabled):
        """Test PR title generation"""
        decision = Decision(
            id="test_123",
            question="Should we implement caching?",
            context="Performance issues",
            decision_text="Yes, add Redis caching",
            decision_type=DecisionType.COMPLEX,
            method="debate",
            rounds=1,
            timestamp=datetime.now()
        )
        
        # Test the title generation logic
        title = pr_service_enabled._generate_descriptive_title(
            decision, 
            "[Complex] Should we implement caching?"
        )
        assert "[Complex]" in title
        assert len(title) <= 100
    
    def test_generate_pr_title_evolution(self, pr_service_enabled):
        """Test PR title generation for evolution"""
        decision = Decision(
            id="evolution_123",
            question="What to improve?",
            context="System evolution",
            decision_text="Implement comprehensive testing framework to ensure reliability",
            decision_type=DecisionType.EVOLUTION,
            method="debate",
            rounds=1,
            timestamp=datetime.now()
        )
        
        title = pr_service_enabled._generate_descriptive_title(
            decision,
            "[Evolution] System self-improvement"
        )
        assert title == "[Evolution] Add comprehensive testing framework"
    
    @pytest.mark.asyncio
    async def test_create_pr_disabled(self, pr_service, sample_decision):
        """Test create_pr when service is disabled"""
        result = await pr_service.create_pr_for_decision(sample_decision)
        assert result is False
    
    def test_get_labels_for_decision(self, pr_service_enabled):
        """Test label generation for decisions"""
        complex_decision = Decision(
            id="test_123",
            question="Complex question",
            context="Context",
            decision_text="Decision",
            decision_type=DecisionType.COMPLEX,
            method="debate",
            rounds=1,
            timestamp=datetime.now()
        )
        
        labels = pr_service_enabled._get_labels_for_decision(complex_decision)
        assert "automated" in labels
        assert "decision" in labels
        assert "complex-decision" in labels
        
        evolution_decision = Decision(
            id="evolution_123",
            question="Evolution",
            context="Context",
            decision_text="Decision",
            decision_type=DecisionType.EVOLUTION,
            method="debate",
            rounds=1,
            timestamp=datetime.now()
        )
        
        labels = pr_service_enabled._get_labels_for_decision(evolution_decision)
        assert "evolution" in labels
        assert "ai-debate" in labels  # Evolution decisions use debate method