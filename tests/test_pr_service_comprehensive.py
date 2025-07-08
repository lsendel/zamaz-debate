"""
Comprehensive tests for PR Service
"""
import pytest
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from services.pr_service import PRService
from domain.models import (
    Decision, Debate, PullRequest, DecisionType, PRStatus, ImplementationAssignee
)


class TestPRServiceComprehensive:
    """Comprehensive test suite for PR Service"""
    
    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Setup test environment"""
        # Save original values
        original_pr = os.environ.get("CREATE_PR_FOR_DECISIONS")
        original_token = os.environ.get("GITHUB_TOKEN")
        original_push = os.environ.get("AUTO_PUSH_PR")
        
        # Set test values
        os.environ["CREATE_PR_FOR_DECISIONS"] = "true"
        os.environ["GITHUB_TOKEN"] = "test-github-token"
        os.environ["AUTO_PUSH_PR"] = "false"
        
        yield
        
        # Restore
        if original_pr is not None:
            os.environ["CREATE_PR_FOR_DECISIONS"] = original_pr
        else:
            os.environ.pop("CREATE_PR_FOR_DECISIONS", None)
            
        if original_token is not None:
            os.environ["GITHUB_TOKEN"] = original_token
        else:
            os.environ.pop("GITHUB_TOKEN", None)
            
        if original_push is not None:
            os.environ["AUTO_PUSH_PR"] = original_push
        else:
            os.environ.pop("AUTO_PUSH_PR", None)
    
    @pytest.fixture
    def pr_service(self):
        """Create PR service"""
        return PRService()
    
    @pytest.fixture
    def sample_decision(self):
        """Create sample decision"""
        return Decision(
            id="decision_123",
            question="Should we implement feature X?",
            context="Feature X would improve performance",
            decision_text="Yes, implement feature X",
            decision_type=DecisionType.COMPLEX,
            method="debate",
            rounds=3,
            timestamp=datetime.now()
        )
    
    @pytest.fixture
    def sample_debate(self):
        """Create sample debate"""
        return Debate(
            id="debate_123",
            question="Should we implement feature X?",
            context="Feature X would improve performance",
            rounds=[{
                "round": 1,
                "claude": "I recommend implementing feature X",
                "gemini": "I agree with implementing feature X"
            }],
            final_decision="Implement feature X",
            complexity="complex",
            start_time=datetime.now(),
            end_time=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_create_pr_for_complex_decision(self, pr_service, sample_decision, sample_debate):
        """Test creating PR for complex decision"""
        with patch.object(pr_service, '_create_branch', return_value=True):
            with patch.object(pr_service, '_save_pr_draft', return_value=None):
                pr = await pr_service.create_pr_for_decision(sample_decision, sample_debate)
        
        assert pr is not None
        assert isinstance(pr, PullRequest)
        assert pr.branch_name == f"decision/complex/decision_123"
        assert "[Complex]" in pr.title
    
    @pytest.mark.asyncio
    async def test_create_pr_for_evolution_decision(self, pr_service):
        """Test creating PR for evolution decision"""
        evolution_decision = Decision(
            id="evolution_123",
            question="What improvement should we make?",
            context="System evolution",
            decision_text="Add testing framework",
            decision_type=DecisionType.EVOLUTION,
            method="debate",
            rounds=2,
            timestamp=datetime.now(),
            implementation_assignee=ImplementationAssignee.CLAUDE
        )
        
        with patch.object(pr_service, '_create_branch', return_value=True):
            with patch.object(pr_service, '_save_pr_draft', return_value=None):
                pr = await pr_service.create_pr_for_decision(evolution_decision, None)
        
        assert pr is not None
        assert "[Evolution]" in pr.title
        assert "testing" in pr.title.lower()
    
    def test_generate_pr(self, pr_service, sample_decision, sample_debate):
        """Test PR generation"""
        pr = pr_service._generate_pr(sample_decision, sample_debate)
        
        assert pr is not None
        assert pr.branch_name == "decision/complex/decision_123"
        assert pr.base_branch == "main"
        assert pr.assignee in ["claude", "gemini-bot", "human"]
        assert "ai-debate" in pr.labels
    
    def test_generate_descriptive_title_evolution(self, pr_service):
        """Test descriptive title generation for evolution"""
        evolution = Decision(
            id="evo_123",
            question="What improvement?",
            context="",
            decision_text="We should add comprehensive testing framework with pytest",
            decision_type=DecisionType.EVOLUTION,
            method="debate",
            rounds=1,
            timestamp=datetime.now()
        )
        
        title = pr_service._generate_descriptive_title(evolution, "[Evolution] System improvement")
        assert "[Evolution] Add comprehensive testing framework" == title
    
    def test_generate_descriptive_title_monitoring(self, pr_service):
        """Test title generation for monitoring improvements"""
        decision = Decision(
            id="evo_124",
            question="",
            context="",
            decision_text="Implement monitoring and observability stack",
            decision_type=DecisionType.EVOLUTION,
            method="debate",
            rounds=1,
            timestamp=datetime.now()
        )
        
        title = pr_service._generate_descriptive_title(decision, "default")
        assert "[Evolution] Implement monitoring and observability" == title
    
    def test_get_labels_for_decision_complex(self, pr_service, sample_decision):
        """Test label generation for complex decision"""
        labels = pr_service._get_labels_for_decision(sample_decision)
        
        assert "ai-debate" in labels
        assert "automated" in labels
        assert "decision" in labels
        assert "complex-decision" in labels
    
    def test_get_labels_for_decision_evolution(self, pr_service):
        """Test label generation for evolution decision"""
        evolution = Decision(
            id="evo_123",
            question="",
            context="",
            decision_text="",
            decision_type=DecisionType.EVOLUTION,
            method="debate",
            rounds=1,
            timestamp=datetime.now()
        )
        
        labels = pr_service._get_labels_for_decision(evolution)
        assert "evolution" in labels
    
    def test_should_create_pr_enabled(self, pr_service, sample_decision):
        """Test should create PR when enabled"""
        assert pr_service.should_create_pr(sample_decision) is True
    
    def test_should_create_pr_disabled(self, sample_decision):
        """Test should not create PR when disabled"""
        os.environ["CREATE_PR_FOR_DECISIONS"] = "false"
        service = PRService()
        assert service.should_create_pr(sample_decision) is False
    
    def test_should_create_pr_for_simple(self, pr_service):
        """Test should not create PR for simple decisions"""
        simple = Decision(
            id="simple_123",
            question="Rename variable?",
            context="",
            decision_text="Yes",
            decision_type=DecisionType.SIMPLE,
            method="direct",
            rounds=0,
            timestamp=datetime.now()
        )
        
        assert pr_service.should_create_pr(simple) is False
    
    @pytest.mark.asyncio
    async def test_create_pr_disabled_returns_false(self, sample_decision):
        """Test PR creation returns False when disabled"""
        os.environ["CREATE_PR_FOR_DECISIONS"] = "false"
        service = PRService()
        
        result = await service.create_pr_for_decision(sample_decision, None)
        assert result is False  # PR service returns False, not None
    
    def test_get_assignee_username_claude(self, pr_service):
        """Test getting Claude's username"""
        # Clear any existing env vars that might interfere
        original = os.environ.get("CLAUDE_GITHUB_USERNAME")
        try:
            os.environ.pop("CLAUDE_GITHUB_USERNAME", None)
            username = pr_service._get_assignee_username(ImplementationAssignee.CLAUDE)
            assert username == "claude"
        finally:
            if original:
                os.environ["CLAUDE_GITHUB_USERNAME"] = original
    
    def test_get_assignee_username_gemini(self, pr_service):
        """Test getting Gemini's username"""
        # Clear any existing env vars that might interfere
        original = os.environ.get("GEMINI_GITHUB_USERNAME")
        try:
            os.environ.pop("GEMINI_GITHUB_USERNAME", None)
            username = pr_service._get_assignee_username(ImplementationAssignee.GEMINI)
            assert username == "gemini-bot"
        finally:
            if original:
                os.environ["GEMINI_GITHUB_USERNAME"] = original
    
    def test_get_assignee_username_human(self, pr_service):
        """Test getting human username"""
        # Clear any existing env vars that might interfere
        original = os.environ.get("HUMAN_GITHUB_USERNAME")
        try:
            os.environ.pop("HUMAN_GITHUB_USERNAME", None)
            username = pr_service._get_assignee_username(ImplementationAssignee.HUMAN)
            assert username == "human"
        finally:
            if original:
                os.environ["HUMAN_GITHUB_USERNAME"] = original
    
    @pytest.mark.asyncio
    async def test_create_branch(self, pr_service):
        """Test branch creation"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = await pr_service._create_branch("test-branch")
            
            assert result is True
            # Should call git checkout
            assert any("checkout" in str(call) for call in mock_run.call_args_list)
    
    @pytest.mark.asyncio
    async def test_save_pr_draft(self, pr_service, sample_decision):
        """Test saving PR draft"""
        pr = pr_service._generate_pr(sample_decision, None)
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            await pr_service._save_pr_draft(pr)
            
            # Should write to PR drafts directory
            mock_open.assert_called()
            assert "pr_drafts" in str(mock_open.call_args[0][0])
    
    def test_generate_pr_body_with_debate(self, pr_service, sample_decision, sample_debate):
        """Test PR body generation with debate details"""
        pr = pr_service._generate_pr(sample_decision, sample_debate)
        
        # Check that debate summary is included
        assert "Debate Summary" in pr.body
        assert sample_debate.id in pr.body
        assert "Full Debate Analysis" in pr.body
        
        # Check implementation assignment
        assert "Implementation Task for Claude" in pr.body
        assert "@claude" in pr.body
    
    def test_implementation_assignment_evolution(self, pr_service):
        """Test implementation assignment for evolution decisions"""
        evolution = Decision(
            id="evo_1",
            question="",
            context="",
            decision_text="",
            decision_type=DecisionType.EVOLUTION,
            method="debate",
            rounds=1,
            timestamp=datetime.now()
        )
        
        pr = pr_service._generate_pr(evolution, None)
        # Evolution decisions should be assigned to Claude
        assert pr.assignee == "claude"
    
    def test_generate_pr_with_custom_assignee(self, pr_service):
        """Test PR generation with custom assignee from environment"""
        # Save original value
        original_claude = os.environ.get("CLAUDE_GITHUB_USERNAME")
        
        try:
            os.environ["CLAUDE_GITHUB_USERNAME"] = "custom-claude"
            
            decision = Decision(
                id="dec_1",
                question="",
                context="",
                decision_text="",
                decision_type=DecisionType.EVOLUTION,
                method="debate",
                rounds=1,
                timestamp=datetime.now(),
                implementation_assignee=ImplementationAssignee.CLAUDE
            )
            
            pr = pr_service._generate_pr(decision, None)
            assert pr.assignee == "custom-claude"
        
        finally:
            # Always cleanup
            if original_claude is not None:
                os.environ["CLAUDE_GITHUB_USERNAME"] = original_claude
            else:
                os.environ.pop("CLAUDE_GITHUB_USERNAME", None)