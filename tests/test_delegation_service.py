"""
Comprehensive tests for Delegation Service
"""

import pytest
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from services.delegation_service import DelegationService
from domain.models import Decision, Debate, DecisionType, ImplementationAssignee


class TestDelegationService:
    """Test suite for Delegation Service"""

    @pytest.fixture
    def delegation_service(self):
        """Create delegation service"""
        return DelegationService()

    @pytest.fixture
    def simple_decision(self):
        """Create simple decision"""
        return Decision(
            id="simple_123",
            question="Should we rename this variable?",
            context="",
            decision_text="Yes, rename to user_count",
            decision_type=DecisionType.SIMPLE,
            method="direct",
            rounds=0,
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def complex_decision(self):
        """Create complex decision"""
        return Decision(
            id="complex_123",
            question="What architecture should we use for the new microservices?",
            context="High traffic, need scalability",
            decision_text="Use event-driven architecture with Kafka",
            decision_type=DecisionType.COMPLEX,
            method="debate",
            rounds=3,
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def evolution_decision(self):
        """Create evolution decision"""
        return Decision(
            id="evolution_123",
            question="What improvement should we make?",
            context="System evolution",
            decision_text="Add comprehensive testing framework",
            decision_type=DecisionType.EVOLUTION,
            method="debate",
            rounds=2,
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def sample_debate(self):
        """Create sample debate"""
        return Debate(
            id="debate_123",
            question="What architecture should we use?",
            context="High traffic system",
            rounds=[
                {
                    "round": 1,
                    "claude": "I recommend event-driven architecture",
                    "gemini": "I agree, event-driven is best",
                }
            ],
            final_decision="Use event-driven architecture",
            complexity="complex",
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

    def test_determine_implementation_assignment_simple(self, delegation_service, simple_decision):
        """Test assignment for simple decision"""
        assignee, complexity = delegation_service.determine_implementation_assignment(simple_decision)

        assert assignee == ImplementationAssignee.GEMINI
        assert complexity == "moderate"  # Only has 1 simple keyword, so it's moderate

    def test_determine_implementation_assignment_complex(self, delegation_service, complex_decision):
        """Test assignment for complex decision"""
        assignee, complexity = delegation_service.determine_implementation_assignment(complex_decision)

        assert assignee == ImplementationAssignee.CLAUDE
        assert complexity == "complex"

    def test_determine_implementation_assignment_evolution(self, delegation_service, evolution_decision):
        """Test assignment for evolution decision"""
        assignee, complexity = delegation_service.determine_implementation_assignment(evolution_decision)

        assert assignee == ImplementationAssignee.CLAUDE
        assert complexity == "complex"

    def test_assess_implementation_complexity_by_keywords(self, delegation_service):
        """Test complexity assessment by keywords"""
        # Architecture decision
        arch_decision = Decision(
            id="arch_123",
            question="What database architecture should we use?",
            context="",
            decision_text="Use sharded MongoDB",
            decision_type=DecisionType.COMPLEX,
            method="debate",
            rounds=2,
            timestamp=datetime.now(),
        )

        complexity = delegation_service._assess_implementation_complexity(arch_decision)
        assert complexity == "complex"

        # Refactoring decision
        refactor_decision = Decision(
            id="refactor_123",
            question="Should we refactor the payment module?",
            context="",
            decision_text="Yes, refactor for better maintainability",
            decision_type=DecisionType.COMPLEX,
            method="debate",
            rounds=2,
            timestamp=datetime.now(),
        )

        complexity = delegation_service._assess_implementation_complexity(refactor_decision)
        assert complexity == "complex"

    def test_assess_implementation_complexity_by_decision_text_length(self, delegation_service):
        """Test complexity assessment by decision text length"""
        # Long decision text
        long_decision = Decision(
            id="long_123",
            question="How to improve performance?",
            context="",
            decision_text="A" * 300,  # Long text
            decision_type=DecisionType.COMPLEX,
            method="debate",
            rounds=1,
            timestamp=datetime.now(),
        )

        complexity = delegation_service._assess_implementation_complexity(long_decision)
        assert complexity == "complex"

        # Short decision text
        short_decision = Decision(
            id="short_123",
            question="Fix typo?",
            context="",
            decision_text="Yes",
            decision_type=DecisionType.SIMPLE,
            method="direct",
            rounds=0,
            timestamp=datetime.now(),
        )

        complexity = delegation_service._assess_implementation_complexity(short_decision)
        assert complexity == "moderate"  # Only has 1 simple keyword (typo)

    def test_assess_implementation_complexity_with_debate(self, delegation_service, complex_decision, sample_debate):
        """Test complexity assessment with debate"""
        complexity = delegation_service._assess_implementation_complexity(complex_decision, sample_debate)

        assert complexity == "complex"

    def test_get_implementation_instructions_claude(self, delegation_service, complex_decision):
        """Test getting implementation instructions for Claude"""
        instructions = delegation_service.get_implementation_instructions(
            complex_decision, ImplementationAssignee.CLAUDE
        )

        assert instructions is not None
        assert "Implementation Task for Claude" in instructions
        assert "Decision" in instructions
        assert "Implementation Guidelines" in instructions
        assert complex_decision.decision_text[:200] in instructions

    def test_get_implementation_instructions_gemini(self, delegation_service, simple_decision):
        """Test getting implementation instructions for Gemini"""
        instructions = delegation_service.get_implementation_instructions(
            simple_decision, ImplementationAssignee.GEMINI
        )

        assert instructions is not None
        assert "Implementation Task for Gemini" in instructions
        assert "Decision" in instructions
        assert simple_decision.decision_text[:200] in instructions

    def test_get_implementation_instructions_human(self, delegation_service, complex_decision):
        """Test getting implementation instructions for human"""
        instructions = delegation_service.get_implementation_instructions(
            complex_decision, ImplementationAssignee.HUMAN
        )

        assert instructions is not None
        assert "Human Intervention" in instructions
        assert complex_decision.decision_text[:200] in instructions

    def test_determine_reviewer(self, delegation_service):
        """Test getting reviewer for assignee"""
        assert delegation_service.determine_reviewer(ImplementationAssignee.CLAUDE) == "gemini-bot"

        assert delegation_service.determine_reviewer(ImplementationAssignee.GEMINI) == "codex"

        assert delegation_service.determine_reviewer(ImplementationAssignee.HUMAN) == "human"
