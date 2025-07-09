"""
Debate Context Repository Interfaces

Repository interfaces define the contract for data access within the debate context.
These are interfaces only - implementations will be provided by the infrastructure layer.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .aggregates import DebateSession, Decision
from .value_objects import DecisionCriteria, Topic


class DebateRepository(ABC):
    """
    Repository interface for DebateSession aggregate

    Provides methods for storing, retrieving, and querying debate sessions.
    """

    @abstractmethod
    async def save(self, debate_session: DebateSession) -> None:
        """
        Save a debate session to the repository

        Args:
            debate_session: The debate session to save
        """
        pass

    @abstractmethod
    async def get_by_id(self, debate_id: UUID) -> Optional[DebateSession]:
        """
        Retrieve a debate session by its ID

        Args:
            debate_id: The unique identifier of the debate session

        Returns:
            Optional[DebateSession]: The debate session if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_topic(self, topic: Topic) -> List[DebateSession]:
        """
        Find debate sessions by topic

        Args:
            topic: The debate topic to search for

        Returns:
            List[DebateSession]: List of debate sessions matching the topic
        """
        pass

    @abstractmethod
    async def find_by_participant(self, participant: str) -> List[DebateSession]:
        """
        Find debate sessions by participant

        Args:
            participant: The participant to search for

        Returns:
            List[DebateSession]: List of debate sessions with the participant
        """
        pass

    @abstractmethod
    async def find_by_status(self, status: str) -> List[DebateSession]:
        """
        Find debate sessions by status

        Args:
            status: The status to search for

        Returns:
            List[DebateSession]: List of debate sessions with the status
        """
        pass

    @abstractmethod
    async def find_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[DebateSession]:
        """
        Find debate sessions within a date range

        Args:
            start_date: The start date
            end_date: The end date

        Returns:
            List[DebateSession]: List of debate sessions within the date range
        """
        pass

    @abstractmethod
    async def find_completed_debates(self) -> List[DebateSession]:
        """
        Find all completed debate sessions

        Returns:
            List[DebateSession]: List of completed debate sessions
        """
        pass

    @abstractmethod
    async def find_active_debates(self) -> List[DebateSession]:
        """
        Find all active debate sessions

        Returns:
            List[DebateSession]: List of active debate sessions
        """
        pass

    @abstractmethod
    async def delete(self, debate_id: UUID) -> bool:
        """
        Delete a debate session

        Args:
            debate_id: The unique identifier of the debate session to delete

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    async def exists(self, debate_id: UUID) -> bool:
        """
        Check if a debate session exists

        Args:
            debate_id: The unique identifier of the debate session

        Returns:
            bool: True if the debate session exists, False otherwise
        """
        pass

    @abstractmethod
    async def count_by_participant(self, participant: str) -> int:
        """
        Count debate sessions by participant

        Args:
            participant: The participant to count for

        Returns:
            int: Number of debate sessions for the participant
        """
        pass

    @abstractmethod
    async def get_debate_statistics(self) -> Dict[str, Any]:
        """
        Get overall debate statistics

        Returns:
            Dict[str, Any]: Statistics about debates
        """
        pass


class DecisionRepository(ABC):
    """
    Repository interface for Decision aggregate

    Provides methods for storing, retrieving, and querying decisions.
    """

    @abstractmethod
    async def save(self, decision: Decision) -> None:
        """
        Save a decision to the repository

        Args:
            decision: The decision to save
        """
        pass

    @abstractmethod
    async def get_by_id(self, decision_id: UUID) -> Optional[Decision]:
        """
        Retrieve a decision by its ID

        Args:
            decision_id: The unique identifier of the decision

        Returns:
            Optional[Decision]: The decision if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_debate_id(self, debate_id: UUID) -> List[Decision]:
        """
        Find decisions by debate ID

        Args:
            debate_id: The debate ID to search for

        Returns:
            List[Decision]: List of decisions from the debate
        """
        pass

    @abstractmethod
    async def find_by_type(self, decision_type: str) -> List[Decision]:
        """
        Find decisions by type

        Args:
            decision_type: The decision type to search for

        Returns:
            List[Decision]: List of decisions of the specified type
        """
        pass

    @abstractmethod
    async def find_by_question(self, question: str) -> List[Decision]:
        """
        Find decisions by question text

        Args:
            question: The question text to search for

        Returns:
            List[Decision]: List of decisions matching the question
        """
        pass

    @abstractmethod
    async def find_by_confidence_range(
        self, min_confidence: float, max_confidence: float
    ) -> List[Decision]:
        """
        Find decisions within a confidence range

        Args:
            min_confidence: Minimum confidence level
            max_confidence: Maximum confidence level

        Returns:
            List[Decision]: List of decisions within the confidence range
        """
        pass

    @abstractmethod
    async def find_requiring_implementation(self) -> List[Decision]:
        """
        Find decisions that require implementation

        Returns:
            List[Decision]: List of decisions requiring implementation
        """
        pass

    @abstractmethod
    async def find_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Decision]:
        """
        Find decisions within a date range

        Args:
            start_date: The start date
            end_date: The end date

        Returns:
            List[Decision]: List of decisions within the date range
        """
        pass

    @abstractmethod
    async def find_recent_decisions(self, limit: int = 10) -> List[Decision]:
        """
        Find recent decisions

        Args:
            limit: Maximum number of decisions to return

        Returns:
            List[Decision]: List of recent decisions
        """
        pass

    @abstractmethod
    async def delete(self, decision_id: UUID) -> bool:
        """
        Delete a decision

        Args:
            decision_id: The unique identifier of the decision to delete

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    async def exists(self, decision_id: UUID) -> bool:
        """
        Check if a decision exists

        Args:
            decision_id: The unique identifier of the decision

        Returns:
            bool: True if the decision exists, False otherwise
        """
        pass

    @abstractmethod
    async def count_by_type(self, decision_type: str) -> int:
        """
        Count decisions by type

        Args:
            decision_type: The decision type to count

        Returns:
            int: Number of decisions of the specified type
        """
        pass

    @abstractmethod
    async def get_decision_statistics(self) -> Dict[str, Any]:
        """
        Get overall decision statistics

        Returns:
            Dict[str, Any]: Statistics about decisions
        """
        pass


class DebateQueryRepository(ABC):
    """
    Repository interface for complex queries across debate and decision aggregates

    Provides methods for analytics and reporting across multiple aggregates.
    """

    @abstractmethod
    async def find_debates_with_decisions(self) -> List[Dict[str, Any]]:
        """
        Find debates that resulted in decisions

        Returns:
            List[Dict[str, Any]]: List of debates with their associated decisions
        """
        pass

    @abstractmethod
    async def find_participant_performance(self, participant: str) -> Dict[str, Any]:
        """
        Find performance metrics for a participant

        Args:
            participant: The participant to analyze

        Returns:
            Dict[str, Any]: Performance metrics for the participant
        """
        pass

    @abstractmethod
    async def find_debate_effectiveness_metrics(self) -> Dict[str, Any]:
        """
        Find effectiveness metrics for debates

        Returns:
            Dict[str, Any]: Effectiveness metrics
        """
        pass

    @abstractmethod
    async def find_decision_accuracy_metrics(self) -> Dict[str, Any]:
        """
        Find accuracy metrics for decisions

        Returns:
            Dict[str, Any]: Accuracy metrics
        """
        pass

    @abstractmethod
    async def find_topic_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Find trending topics over a period

        Args:
            days: Number of days to analyze

        Returns:
            List[Dict[str, Any]]: Trending topics with statistics
        """
        pass

    @abstractmethod
    async def find_consensus_patterns(self) -> Dict[str, Any]:
        """
        Find patterns in consensus building

        Returns:
            Dict[str, Any]: Consensus patterns and statistics
        """
        pass


class DebateSpecification(ABC):
    """
    Specification interface for complex debate queries

    Implements the Specification pattern for flexible query building.
    """

    @abstractmethod
    def is_satisfied_by(self, debate_session: DebateSession) -> bool:
        """
        Check if a debate session satisfies this specification

        Args:
            debate_session: The debate session to check

        Returns:
            bool: True if the specification is satisfied
        """
        pass

    @abstractmethod
    def and_specification(self, other: "DebateSpecification") -> "DebateSpecification":
        """
        Create an AND specification

        Args:
            other: The other specification

        Returns:
            DebateSpecification: Combined specification
        """
        pass

    @abstractmethod
    def or_specification(self, other: "DebateSpecification") -> "DebateSpecification":
        """
        Create an OR specification

        Args:
            other: The other specification

        Returns:
            DebateSpecification: Combined specification
        """
        pass

    @abstractmethod
    def not_specification(self) -> "DebateSpecification":
        """
        Create a NOT specification

        Returns:
            DebateSpecification: Negated specification
        """
        pass


class DecisionSpecification(ABC):
    """
    Specification interface for complex decision queries

    Implements the Specification pattern for flexible query building.
    """

    @abstractmethod
    def is_satisfied_by(self, decision: Decision) -> bool:
        """
        Check if a decision satisfies this specification

        Args:
            decision: The decision to check

        Returns:
            bool: True if the specification is satisfied
        """
        pass

    @abstractmethod
    def and_specification(
        self, other: "DecisionSpecification"
    ) -> "DecisionSpecification":
        """
        Create an AND specification

        Args:
            other: The other specification

        Returns:
            DecisionSpecification: Combined specification
        """
        pass

    @abstractmethod
    def or_specification(
        self, other: "DecisionSpecification"
    ) -> "DecisionSpecification":
        """
        Create an OR specification

        Args:
            other: The other specification

        Returns:
            DecisionSpecification: Combined specification
        """
        pass

    @abstractmethod
    def not_specification(self) -> "DecisionSpecification":
        """
        Create a NOT specification

        Returns:
            DecisionSpecification: Negated specification
        """
        pass
