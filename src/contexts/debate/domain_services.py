"""
Debate Context Domain Services

Domain services contain business logic that doesn't naturally fit within aggregates.
They coordinate between aggregates and implement complex business rules.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .aggregates import DebateSession, Decision, DecisionType
from .events import ComplexityAssessed, DebateMetricsCalculated
from .value_objects import (
    Argument,
    ArgumentType,
    Consensus,
    ConsensusLevel,
    DebateMetrics,
    DecisionCriteria,
    Topic,
)


class ComplexityAssessment:
    """
    Domain service for assessing decision complexity

    Determines whether a decision requires a debate based on various criteria.
    """

    def __init__(self):
        self.complexity_thresholds = {"simple": 0.3, "moderate": 0.6, "complex": 0.8}

    def assess_decision_complexity(self, question: str, context: Dict[str, Any] = None) -> DecisionCriteria:
        """
        Assess the complexity of a decision based on the question and context

        Args:
            question: The decision question
            context: Additional context for assessment

        Returns:
            DecisionCriteria: The assessed criteria
        """
        if context is None:
            context = {}

        # Analyze question complexity
        impact = self._assess_impact(question, context)
        complexity = self._assess_complexity(question, context)
        reversibility = self._assess_reversibility(question, context)
        stakeholder_count = self._assess_stakeholder_count(question, context)
        time_sensitivity = self._assess_time_sensitivity(question, context)

        return DecisionCriteria(
            impact=impact,
            complexity=complexity,
            reversibility=reversibility,
            stakeholder_count=stakeholder_count,
            time_sensitivity=time_sensitivity,
        )

    def requires_debate(self, criteria: DecisionCriteria) -> bool:
        """
        Determine if a decision requires a debate based on criteria

        Args:
            criteria: The decision criteria

        Returns:
            bool: True if debate is required
        """
        return criteria.complexity_score >= self.complexity_thresholds["moderate"]

    def determine_decision_type(self, criteria: DecisionCriteria) -> DecisionType:
        """
        Determine the type of decision based on criteria

        Args:
            criteria: The decision criteria

        Returns:
            DecisionType: The appropriate decision type
        """
        score = criteria.complexity_score

        if score < self.complexity_thresholds["simple"]:
            return DecisionType.SIMPLE
        elif score < self.complexity_thresholds["complex"]:
            return DecisionType.COMPLEX
        else:
            # Determine if it's architectural or strategic
            if "architect" in criteria.impact.lower() or "system" in criteria.impact.lower():
                return DecisionType.ARCHITECTURAL
            else:
                return DecisionType.STRATEGIC

    def _assess_impact(self, question: str, context: Dict[str, Any]) -> str:
        """Assess the impact level of a decision"""
        high_impact_keywords = [
            "architecture",
            "system",
            "major",
            "critical",
            "fundamental",
        ]
        medium_impact_keywords = ["feature", "enhancement", "improve", "optimize"]

        question_lower = question.lower()

        if any(keyword in question_lower for keyword in high_impact_keywords):
            return "high"
        elif any(keyword in question_lower for keyword in medium_impact_keywords):
            return "medium"
        else:
            return "low"

    def _assess_complexity(self, question: str, context: Dict[str, Any]) -> str:
        """Assess the complexity level of a decision"""
        complex_keywords = ["integrate", "refactor", "migrate", "redesign", "transform"]
        medium_keywords = ["implement", "add", "modify", "update", "enhance"]

        question_lower = question.lower()

        if any(keyword in question_lower for keyword in complex_keywords):
            return "high"
        elif any(keyword in question_lower for keyword in medium_keywords):
            return "medium"
        else:
            return "low"

    def _assess_reversibility(self, question: str, context: Dict[str, Any]) -> str:
        """Assess the reversibility of a decision"""
        irreversible_keywords = ["delete", "remove", "migrate", "replace", "deprecate"]
        semi_reversible_keywords = ["refactor", "restructure", "reorganize"]

        question_lower = question.lower()

        if any(keyword in question_lower for keyword in irreversible_keywords):
            return "irreversible"
        elif any(keyword in question_lower for keyword in semi_reversible_keywords):
            return "semi-reversible"
        else:
            return "reversible"

    def _assess_stakeholder_count(self, question: str, context: Dict[str, Any]) -> int:
        """Assess the number of stakeholders affected"""
        # Simple heuristic based on question scope
        if "system" in question.lower() or "architecture" in question.lower():
            return 5  # High stakeholder count
        elif "team" in question.lower() or "project" in question.lower():
            return 3  # Medium stakeholder count
        else:
            return 1  # Low stakeholder count

    def _assess_time_sensitivity(self, question: str, context: Dict[str, Any]) -> str:
        """Assess the time sensitivity of a decision"""
        urgent_keywords = ["urgent", "immediate", "critical", "emergency"]
        moderate_keywords = ["soon", "priority", "important"]

        question_lower = question.lower()

        if any(keyword in question_lower for keyword in urgent_keywords):
            return "urgent"
        elif any(keyword in question_lower for keyword in moderate_keywords):
            return "moderate"
        else:
            return "low"


class ConsensusEvaluation:
    """
    Domain service for evaluating consensus in debates

    Determines when consensus is reached and evaluates the quality of consensus.
    """

    def __init__(self):
        self.consensus_thresholds = {"strong": 0.8, "moderate": 0.6, "weak": 0.4}

    def evaluate_consensus(self, debate_session: DebateSession) -> Optional[Consensus]:
        """
        Evaluate if consensus has been reached in a debate session

        Args:
            debate_session: The debate session to evaluate

        Returns:
            Optional[Consensus]: The consensus if reached, None otherwise
        """
        if not debate_session.rounds:
            return None

        # Analyze arguments from all rounds
        all_arguments = []
        for round_obj in debate_session.rounds:
            all_arguments.extend(round_obj.arguments)

        if len(all_arguments) < 2:
            return None

        # Calculate agreement level
        agreement_score = self._calculate_agreement_score(all_arguments)

        # Determine consensus level
        consensus_level = self._determine_consensus_level(agreement_score)

        if consensus_level == ConsensusLevel.NONE:
            return None

        # Generate consensus value and rationale
        consensus_value = self._generate_consensus_value(all_arguments)
        rationale = self._generate_consensus_rationale(all_arguments, consensus_level)

        return Consensus(
            value=consensus_value,
            level=consensus_level,
            rationale=rationale,
            confidence=agreement_score,
            reached_at=datetime.now(),
        )

    def _calculate_agreement_score(self, arguments: List[Argument]) -> float:
        """Calculate the agreement score based on arguments"""
        if not arguments:
            return 0.0

        # Simple heuristic: higher confidence arguments indicate stronger agreement
        total_confidence = sum(arg.confidence for arg in arguments)
        average_confidence = total_confidence / len(arguments)

        # Consider argument types
        supporting_args = [arg for arg in arguments if arg.type == ArgumentType.SUPPORTING]
        opposing_args = [arg for arg in arguments if arg.type == ArgumentType.OPPOSING]

        if not supporting_args and not opposing_args:
            return average_confidence

        # Calculate balance between supporting and opposing arguments
        support_ratio = len(supporting_args) / len(arguments)

        # Higher support ratio with high confidence indicates stronger consensus
        agreement_score = average_confidence * (0.5 + support_ratio * 0.5)

        return min(1.0, agreement_score)

    def _determine_consensus_level(self, agreement_score: float) -> ConsensusLevel:
        """Determine the consensus level based on agreement score"""
        if agreement_score >= self.consensus_thresholds["strong"]:
            return ConsensusLevel.STRONG
        elif agreement_score >= self.consensus_thresholds["moderate"]:
            return ConsensusLevel.MODERATE
        elif agreement_score >= self.consensus_thresholds["weak"]:
            return ConsensusLevel.WEAK
        else:
            return ConsensusLevel.NONE

    def _generate_consensus_value(self, arguments: List[Argument]) -> str:
        """Generate a consensus value based on arguments"""
        # Simple heuristic: use the most confident supporting argument
        supporting_args = [arg for arg in arguments if arg.type == ArgumentType.SUPPORTING]

        if supporting_args:
            best_arg = max(supporting_args, key=lambda x: x.confidence)
            return f"Consensus based on: {best_arg.content[:100]}..."

        # Fallback to general consensus
        return "General consensus reached based on debate discussion"

    def _generate_consensus_rationale(self, arguments: List[Argument], level: ConsensusLevel) -> str:
        """Generate rationale for the consensus"""
        arg_count = len(arguments)
        participant_count = len(set(arg.participant for arg in arguments))

        rationale = f"Consensus reached based on {arg_count} arguments from {participant_count} participants. "

        if level == ConsensusLevel.STRONG:
            rationale += "Strong agreement with high confidence across all participants."
        elif level == ConsensusLevel.MODERATE:
            rationale += "Moderate agreement with reasonable confidence from most participants."
        else:
            rationale += "Weak agreement with some reservations from participants."

        return rationale


class ArgumentValidation:
    """
    Domain service for validating arguments in debates

    Ensures arguments meet quality standards and are appropriate for the debate context.
    """

    def __init__(self):
        self.min_word_count = 5
        self.max_word_count = 1000
        self.prohibited_words = ["spam", "test", "dummy"]

    def validate_argument(self, argument: Argument, debate_topic: Topic) -> bool:
        """
        Validate an argument for a debate

        Args:
            argument: The argument to validate
            debate_topic: The debate topic

        Returns:
            bool: True if argument is valid
        """
        # Check word count
        if not (self.min_word_count <= argument.word_count <= self.max_word_count):
            return False

        # Check for prohibited content
        if any(word in argument.content.lower() for word in self.prohibited_words):
            return False

        # Check relevance to topic
        if not self._is_relevant_to_topic(argument, debate_topic):
            return False

        # Check argument structure
        if not self._has_valid_structure(argument):
            return False

        return True

    def _is_relevant_to_topic(self, argument: Argument, topic: Topic) -> bool:
        """Check if argument is relevant to the debate topic"""
        # Simple keyword matching
        topic_words = set(topic.value.lower().split())
        argument_words = set(argument.content.lower().split())

        # At least 10% word overlap or specific relevance indicators
        overlap = len(topic_words.intersection(argument_words)) / len(topic_words)
        return overlap >= 0.1

    def _has_valid_structure(self, argument: Argument) -> bool:
        """Check if argument has valid structure"""
        # Must have at least one sentence
        sentences = re.split(r"[.!?]+", argument.content)
        valid_sentences = [s for s in sentences if s.strip()]

        return len(valid_sentences) >= 1


class DebateMetricsCalculator:
    """
    Domain service for calculating debate metrics

    Analyzes debate performance and generates metrics for improvement.
    """

    def calculate_metrics(self, debate_session: DebateSession) -> DebateMetrics:
        """
        Calculate comprehensive metrics for a debate session

        Args:
            debate_session: The completed debate session

        Returns:
            DebateMetrics: Calculated metrics
        """
        if not debate_session.is_completed:
            raise ValueError("Cannot calculate metrics for incomplete debate")

        # Calculate basic metrics
        total_rounds = len(debate_session.rounds)
        total_arguments = sum(len(round_obj.arguments) for round_obj in debate_session.rounds)

        # Calculate average argument length
        all_arguments = []
        for round_obj in debate_session.rounds:
            all_arguments.extend(round_obj.arguments)

        average_argument_length = (
            sum(arg.word_count for arg in all_arguments) / len(all_arguments) if all_arguments else 0.0
        )

        # Calculate timing metrics
        debate_duration = debate_session.completed_at - debate_session.created_at
        debate_duration_minutes = int(debate_duration.total_seconds() / 60)

        # Estimate consensus time (simplified)
        consensus_time_minutes = max(1, debate_duration_minutes // 2)

        # Calculate participant engagement
        participant_engagement = self._calculate_participant_engagement(all_arguments)

        return DebateMetrics(
            total_rounds=total_rounds,
            total_arguments=total_arguments,
            average_argument_length=average_argument_length,
            debate_duration_minutes=debate_duration_minutes,
            consensus_time_minutes=consensus_time_minutes,
            participant_engagement=participant_engagement,
        )

    def _calculate_participant_engagement(self, arguments: List[Argument]) -> Dict[str, float]:
        """Calculate engagement scores for each participant"""
        if not arguments:
            return {}

        participant_stats = {}

        # Count arguments per participant
        for arg in arguments:
            if arg.participant not in participant_stats:
                participant_stats[arg.participant] = {
                    "argument_count": 0,
                    "total_confidence": 0.0,
                    "total_words": 0,
                }

            stats = participant_stats[arg.participant]
            stats["argument_count"] += 1
            stats["total_confidence"] += arg.confidence
            stats["total_words"] += arg.word_count

        # Calculate engagement scores
        engagement_scores = {}
        max_arguments = max(stats["argument_count"] for stats in participant_stats.values())

        for participant, stats in participant_stats.items():
            # Normalize metrics
            argument_ratio = stats["argument_count"] / max_arguments
            avg_confidence = stats["total_confidence"] / stats["argument_count"]
            avg_words = stats["total_words"] / stats["argument_count"]

            # Calculate engagement score (0.0 to 1.0)
            engagement_score = argument_ratio * 0.4 + avg_confidence * 0.4 + min(1.0, avg_words / 100) * 0.2

            engagement_scores[participant] = min(1.0, engagement_score)

        return engagement_scores
