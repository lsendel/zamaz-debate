"""
Unit tests for the Debate Context

This module contains comprehensive unit tests for the debate context aggregates,
value objects, domain services, and business logic.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.contexts.debate.aggregates import DebateSession, Decision, Round, DebateStatus, DecisionType
from src.contexts.debate.value_objects import (
    Argument,
    Topic,
    Consensus,
    ConsensusLevel,
    DecisionCriteria,
    DebateMetrics,
    ArgumentType,
)
from src.contexts.debate.domain_services import (
    ComplexityAssessment,
    ConsensusEvaluation,
    ArgumentValidation,
    DebateMetricsCalculator,
)
from src.contexts.debate.events import DebateInitiated, RoundStarted, DecisionMade


class TestTopic:
    """Test cases for Topic value object"""

    def test_topic_creation(self):
        """Test creating a valid topic"""
        topic = Topic(
            value="Should we implement microservices?", description="Architectural decision", category="architecture"
        )

        assert topic.value == "Should we implement microservices?"
        assert topic.description == "Architectural decision"
        assert topic.category == "architecture"

    def test_topic_validation_empty_value(self):
        """Test topic validation with empty value"""
        with pytest.raises(ValueError, match="Topic value cannot be empty"):
            Topic(value="")

    def test_topic_validation_too_long(self):
        """Test topic validation with too long value"""
        long_value = "x" * 501
        with pytest.raises(ValueError, match="Topic value cannot exceed 500 characters"):
            Topic(value=long_value)

    def test_topic_is_question(self):
        """Test topic question detection"""
        question_topic = Topic(value="Should we do this?")
        statement_topic = Topic(value="We should do this")

        assert question_topic.is_question is True
        assert statement_topic.is_question is False

    def test_topic_word_count(self):
        """Test topic word count calculation"""
        topic = Topic(value="Should we implement microservices architecture")
        assert topic.word_count == 5


class TestArgument:
    """Test cases for Argument value object"""

    def test_argument_creation(self):
        """Test creating a valid argument"""
        argument = Argument(
            content="I believe microservices would improve scalability",
            participant="Claude",
            type=ArgumentType.SUPPORTING,
            timestamp=datetime.now(),
            confidence=0.8,
        )

        assert argument.content == "I believe microservices would improve scalability"
        assert argument.participant == "Claude"
        assert argument.type == ArgumentType.SUPPORTING
        assert argument.confidence == 0.8

    def test_argument_validation_empty_content(self):
        """Test argument validation with empty content"""
        with pytest.raises(ValueError, match="Argument content cannot be empty"):
            Argument(content="", participant="Claude", type=ArgumentType.SUPPORTING, timestamp=datetime.now())

    def test_argument_validation_invalid_confidence(self):
        """Test argument validation with invalid confidence"""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            Argument(
                content="Valid content",
                participant="Claude",
                type=ArgumentType.SUPPORTING,
                timestamp=datetime.now(),
                confidence=1.5,
            )

    def test_argument_strength_score(self):
        """Test argument strength score calculation"""
        argument = Argument(
            content="This is a detailed argument with supporting evidence",
            participant="Claude",
            type=ArgumentType.SUPPORTING,
            timestamp=datetime.now(),
            confidence=0.8,
            supporting_evidence="Research shows that...",
        )

        # Should be higher than confidence due to evidence and length bonuses
        assert argument.strength_score > 0.8
        assert argument.strength_score <= 1.0


class TestConsensus:
    """Test cases for Consensus value object"""

    def test_consensus_creation(self):
        """Test creating a valid consensus"""
        consensus = Consensus(
            value="We should proceed with microservices",
            level=ConsensusLevel.STRONG,
            rationale="All participants agreed after thorough discussion",
            confidence=0.9,
            reached_at=datetime.now(),
        )

        assert consensus.level == ConsensusLevel.STRONG
        assert consensus.confidence == 0.9
        assert consensus.is_actionable is True

    def test_consensus_validation_confidence_level_mismatch(self):
        """Test consensus validation with confidence-level mismatch"""
        with pytest.raises(ValueError, match="Strong consensus requires confidence >= 0.8"):
            Consensus(
                value="Test consensus",
                level=ConsensusLevel.STRONG,
                rationale="Test rationale",
                confidence=0.7,
                reached_at=datetime.now(),
            )

    def test_consensus_requires_review(self):
        """Test consensus review requirement"""
        weak_consensus = Consensus(
            value="Maybe we should do this",
            level=ConsensusLevel.WEAK,
            rationale="Weak agreement",
            confidence=0.5,
            reached_at=datetime.now(),
        )

        assert weak_consensus.requires_review is True
        assert weak_consensus.is_actionable is False


class TestDecisionCriteria:
    """Test cases for DecisionCriteria value object"""

    def test_decision_criteria_creation(self):
        """Test creating valid decision criteria"""
        criteria = DecisionCriteria(
            impact="high",
            complexity="medium",
            reversibility="semi-reversible",
            stakeholder_count=3,
            time_sensitivity="moderate",
        )

        assert criteria.impact == "high"
        assert criteria.complexity == "medium"
        assert criteria.stakeholder_count == 3

    def test_decision_criteria_complexity_score(self):
        """Test complexity score calculation"""
        high_complexity = DecisionCriteria(
            impact="high",
            complexity="high",
            reversibility="irreversible",
            stakeholder_count=10,
            time_sensitivity="urgent",
        )

        low_complexity = DecisionCriteria(
            impact="low", complexity="low", reversibility="reversible", stakeholder_count=1, time_sensitivity="low"
        )

        assert high_complexity.complexity_score > low_complexity.complexity_score
        assert high_complexity.requires_debate is True
        assert low_complexity.requires_debate is False


class TestRound:
    """Test cases for Round entity"""

    def test_round_creation(self):
        """Test creating a round"""
        round_obj = Round(round_number=1)

        assert round_obj.round_number == 1
        assert len(round_obj.arguments) == 0
        assert round_obj.is_completed is False

    def test_round_add_argument(self):
        """Test adding arguments to a round"""
        round_obj = Round(round_number=1)
        argument = Argument(
            content="Test argument", participant="Claude", type=ArgumentType.SUPPORTING, timestamp=datetime.now()
        )

        round_obj.add_argument(argument)

        assert len(round_obj.arguments) == 1
        assert round_obj.arguments[0] == argument

    def test_round_complete(self):
        """Test completing a round"""
        round_obj = Round(round_number=1)
        round_obj.complete()

        assert round_obj.is_completed is True
        assert round_obj.completed_at is not None

    def test_round_add_argument_to_completed(self):
        """Test adding argument to completed round should fail"""
        round_obj = Round(round_number=1)
        round_obj.complete()

        argument = Argument(
            content="Test argument", participant="Claude", type=ArgumentType.SUPPORTING, timestamp=datetime.now()
        )

        with pytest.raises(ValueError, match="Cannot add arguments to completed round"):
            round_obj.add_argument(argument)


class TestDebateSession:
    """Test cases for DebateSession aggregate"""

    def test_debate_session_creation(self):
        """Test creating a debate session"""
        topic = Topic(value="Should we implement microservices?")
        debate = DebateSession(topic=topic, participants=["Claude", "Gemini"])

        assert debate.topic == topic
        assert debate.participants == ["Claude", "Gemini"]
        assert debate.status == DebateStatus.INITIATED
        assert len(debate.get_events()) == 1  # DebateInitiated event

    def test_debate_session_add_participant(self):
        """Test adding participants to a debate"""
        debate = DebateSession()
        debate.add_participant("Claude")
        debate.add_participant("Gemini")

        assert "Claude" in debate.participants
        assert "Gemini" in debate.participants

    def test_debate_session_add_duplicate_participant(self):
        """Test adding duplicate participant should fail"""
        debate = DebateSession()
        debate.add_participant("Claude")

        with pytest.raises(ValueError, match="Participant Claude already in debate"):
            debate.add_participant("Claude")

    def test_debate_session_start_round(self):
        """Test starting a debate round"""
        debate = DebateSession()
        round_obj = debate.start_round()

        assert round_obj.round_number == 1
        assert debate.status == DebateStatus.IN_PROGRESS
        assert len(debate.rounds) == 1
        assert debate.current_round == round_obj

        # Check for RoundStarted event
        events = debate.get_events()
        round_started_events = [e for e in events if e.get("event_type") == "RoundStarted"]
        assert len(round_started_events) == 1

    def test_debate_session_max_rounds(self):
        """Test maximum rounds enforcement"""
        debate = DebateSession(max_rounds=2)

        # Start maximum rounds
        debate.start_round()
        debate.start_round()

        # Should fail on third round
        with pytest.raises(ValueError, match="Maximum rounds"):
            debate.start_round()

    def test_debate_session_make_decision(self):
        """Test making a decision"""
        debate = DebateSession()
        consensus = Consensus(
            value="Proceed with microservices",
            level=ConsensusLevel.STRONG,
            rationale="All agreed",
            confidence=0.9,
            reached_at=datetime.now(),
        )

        debate.reach_consensus(consensus)

        decision = Decision(
            question="Should we implement microservices?",
            type=DecisionType.ARCHITECTURAL,
            recommendation="Yes, implement microservices",
            confidence=0.9,
            debate_id=debate.id,
        )

        debate.make_decision(decision)

        assert debate.decision == decision
        assert debate.status == DebateStatus.COMPLETED
        assert debate.is_completed is True

        # Check for DecisionMade event
        events = debate.get_events()
        decision_made_events = [e for e in events if e.get("event_type") == "DecisionMade"]
        assert len(decision_made_events) == 1


class TestDecision:
    """Test cases for Decision aggregate"""

    def test_decision_creation(self):
        """Test creating a decision"""
        decision = Decision(
            question="Should we implement microservices?",
            type=DecisionType.ARCHITECTURAL,
            rationale="Microservices improve scalability",
            recommendation="Yes, implement microservices",
            confidence=0.8,
        )

        assert decision.question == "Should we implement microservices?"
        assert decision.type == DecisionType.ARCHITECTURAL
        assert decision.confidence == 0.8
        assert decision.requires_debate is True

    def test_decision_validation_empty_question(self):
        """Test decision validation with empty question"""
        with pytest.raises(ValueError, match="Decision question cannot be empty"):
            Decision(question="")

    def test_decision_validation_invalid_confidence(self):
        """Test decision validation with invalid confidence"""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            Decision(question="Valid question?", confidence=1.5)

    def test_decision_complex_without_debate(self):
        """Test complex decision without debate ID should fail"""
        with pytest.raises(ValueError, match="Complex decisions must have an associated debate"):
            Decision(question="Should we implement microservices?", type=DecisionType.COMPLEX, debate_id=None)

    def test_decision_mark_for_implementation(self):
        """Test marking decision for implementation"""
        decision = Decision(question="Should we implement microservices?")
        decision.mark_for_implementation()

        assert decision.implementation_required is True


class TestComplexityAssessment:
    """Test cases for ComplexityAssessment domain service"""

    def test_complexity_assessment_creation(self):
        """Test creating complexity assessment service"""
        service = ComplexityAssessment()
        assert service.complexity_thresholds["simple"] == 0.3
        assert service.complexity_thresholds["moderate"] == 0.6
        assert service.complexity_thresholds["complex"] == 0.8

    def test_assess_decision_complexity(self):
        """Test assessing decision complexity"""
        service = ComplexityAssessment()

        # Test high complexity question
        criteria = service.assess_decision_complexity(
            "Should we migrate the entire system architecture to microservices?"
        )

        assert criteria.complexity_score > 0.5
        assert service.requires_debate(criteria) is True

        # Test low complexity question
        criteria = service.assess_decision_complexity("Should we fix this typo?")

        assert criteria.complexity_score < 0.5
        assert service.requires_debate(criteria) is False

    def test_determine_decision_type(self):
        """Test determining decision type"""
        service = ComplexityAssessment()

        # High complexity architectural decision
        criteria = DecisionCriteria(
            impact="high",
            complexity="high",
            reversibility="irreversible",
            stakeholder_count=10,
            time_sensitivity="urgent",
        )

        decision_type = service.determine_decision_type(criteria)
        assert decision_type in [DecisionType.ARCHITECTURAL, DecisionType.STRATEGIC]


class TestConsensusEvaluation:
    """Test cases for ConsensusEvaluation domain service"""

    def test_consensus_evaluation_creation(self):
        """Test creating consensus evaluation service"""
        service = ConsensusEvaluation()
        assert service.consensus_thresholds["strong"] == 0.8
        assert service.consensus_thresholds["moderate"] == 0.6
        assert service.consensus_thresholds["weak"] == 0.4

    def test_evaluate_consensus_no_arguments(self):
        """Test consensus evaluation with no arguments"""
        service = ConsensusEvaluation()
        debate = DebateSession()

        consensus = service.evaluate_consensus(debate)
        assert consensus is None

    def test_evaluate_consensus_with_arguments(self):
        """Test consensus evaluation with arguments"""
        service = ConsensusEvaluation()
        debate = DebateSession()

        # Add a round with arguments
        round_obj = debate.start_round()

        # Add supporting arguments
        for i in range(3):
            argument = Argument(
                content=f"Supporting argument {i}",
                participant=f"Participant{i}",
                type=ArgumentType.SUPPORTING,
                timestamp=datetime.now(),
                confidence=0.8,
            )
            round_obj.add_argument(argument)

        consensus = service.evaluate_consensus(debate)

        assert consensus is not None
        assert consensus.level in [ConsensusLevel.STRONG, ConsensusLevel.MODERATE]
        assert consensus.confidence > 0.5


class TestArgumentValidation:
    """Test cases for ArgumentValidation domain service"""

    def test_argument_validation_service(self):
        """Test argument validation service"""
        service = ArgumentValidation()
        topic = Topic(value="Should we implement microservices?")

        # Valid argument
        valid_argument = Argument(
            content="Microservices improve scalability and maintainability",
            participant="Claude",
            type=ArgumentType.SUPPORTING,
            timestamp=datetime.now(),
            confidence=0.8,
        )

        assert service.validate_argument(valid_argument, topic) is True

        # Invalid argument (too short)
        invalid_argument = Argument(
            content="Yes", participant="Claude", type=ArgumentType.SUPPORTING, timestamp=datetime.now(), confidence=0.8
        )

        assert service.validate_argument(invalid_argument, topic) is False


class TestDebateMetricsCalculator:
    """Test cases for DebateMetricsCalculator domain service"""

    def test_calculate_metrics_incomplete_debate(self):
        """Test calculating metrics for incomplete debate should fail"""
        service = DebateMetricsCalculator()
        debate = DebateSession()

        with pytest.raises(ValueError, match="Cannot calculate metrics for incomplete debate"):
            service.calculate_metrics(debate)

    def test_calculate_metrics_completed_debate(self):
        """Test calculating metrics for completed debate"""
        service = DebateMetricsCalculator()

        # Create a completed debate
        debate = DebateSession()
        debate.add_participant("Claude")
        debate.add_participant("Gemini")

        # Add rounds with arguments
        round1 = debate.start_round()
        round1.add_argument(
            Argument(
                content="This is a test argument",
                participant="Claude",
                type=ArgumentType.SUPPORTING,
                timestamp=datetime.now(),
                confidence=0.8,
            )
        )
        round1.complete()

        # Complete the debate
        consensus = Consensus(
            value="Test consensus",
            level=ConsensusLevel.MODERATE,
            rationale="Test rationale",
            confidence=0.7,
            reached_at=datetime.now(),
        )
        debate.reach_consensus(consensus)

        decision = Decision(
            question="Test question?",
            type=DecisionType.SIMPLE,
            recommendation="Test recommendation",
            confidence=0.7,
            debate_id=debate.id,
        )
        debate.make_decision(decision)

        # Calculate metrics
        metrics = service.calculate_metrics(debate)

        assert metrics.total_rounds == 1
        assert metrics.total_arguments == 1
        assert metrics.average_argument_length > 0
        assert metrics.debate_duration_minutes >= 0
        assert len(metrics.participant_engagement) == 1
        assert "Claude" in metrics.participant_engagement


if __name__ == "__main__":
    pytest.main([__file__])
