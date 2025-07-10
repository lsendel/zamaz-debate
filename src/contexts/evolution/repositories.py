"""
Evolution Context Repository Interfaces

Repository interfaces for the evolution context following DDD patterns.
These abstractions hide persistence details from the domain layer.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from .aggregates import Evolution, EvolutionHistory, Improvement
from .value_objects import ImprovementArea, ImprovementSuggestion


class EvolutionRepository(ABC):
    """
    Repository interface for Evolution aggregate
    
    Provides persistence operations for system evolutions.
    """
    
    @abstractmethod
    async def save(self, evolution: Evolution) -> None:
        """
        Save an evolution
        
        Args:
            evolution: The evolution to save
        """
        pass
    
    @abstractmethod
    async def find_by_id(self, evolution_id: UUID) -> Optional[Evolution]:
        """
        Find an evolution by ID
        
        Args:
            evolution_id: The ID of the evolution
            
        Returns:
            The evolution if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_status(self, status: str) -> List[Evolution]:
        """
        Find evolutions by status
        
        Args:
            status: The evolution status
            
        Returns:
            List of evolutions with the given status
        """
        pass
    
    @abstractmethod
    async def find_active(self) -> List[Evolution]:
        """
        Find all active (in-progress) evolutions
        
        Returns:
            List of active evolutions
        """
        pass
    
    @abstractmethod
    async def find_by_trigger(self, trigger_type: str) -> List[Evolution]:
        """
        Find evolutions by trigger type
        
        Args:
            trigger_type: The type of trigger (scheduled, performance, etc.)
            
        Returns:
            List of evolutions with the given trigger
        """
        pass
    
    @abstractmethod
    async def find_completed_between(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Evolution]:
        """
        Find evolutions completed between dates
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of completed evolutions
        """
        pass
    
    @abstractmethod
    async def find_with_improvement(self, improvement_area: ImprovementArea) -> List[Evolution]:
        """
        Find evolutions that include improvements in a specific area
        
        Args:
            improvement_area: The area of improvement
            
        Returns:
            List of evolutions with improvements in that area
        """
        pass
    
    @abstractmethod
    async def update(self, evolution: Evolution) -> bool:
        """
        Update an evolution
        
        Args:
            evolution: The evolution to update
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, evolution_id: UUID) -> bool:
        """
        Delete an evolution
        
        Args:
            evolution_id: The ID of the evolution to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, evolution_id: UUID) -> bool:
        """
        Check if an evolution exists
        
        Args:
            evolution_id: The ID to check
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def count_by_status(self) -> Dict[str, int]:
        """
        Count evolutions by status
        
        Returns:
            Dictionary with status as key and count as value
        """
        pass
    
    @abstractmethod
    async def get_success_rate(self, days: int = 30) -> float:
        """
        Calculate evolution success rate over a period
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Success rate as a percentage
        """
        pass


class ImprovementRepository(ABC):
    """
    Repository interface for Improvement entity
    
    Provides persistence operations for improvement suggestions.
    Note: Improvements are part of the Evolution aggregate, but
    this repository allows for cross-aggregate queries.
    """
    
    @abstractmethod
    async def find_by_id(self, improvement_id: UUID) -> Optional[Improvement]:
        """
        Find an improvement by ID
        
        Args:
            improvement_id: The ID of the improvement
            
        Returns:
            The improvement if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_area(self, area: ImprovementArea) -> List[Improvement]:
        """
        Find improvements by area
        
        Args:
            area: The improvement area
            
        Returns:
            List of improvements in that area
        """
        pass
    
    @abstractmethod
    async def find_by_status(self, status: str) -> List[Improvement]:
        """
        Find improvements by status
        
        Args:
            status: The improvement status
            
        Returns:
            List of improvements with the given status
        """
        pass
    
    @abstractmethod
    async def find_approved_not_implemented(self) -> List[Improvement]:
        """
        Find approved improvements that haven't been implemented yet
        
        Returns:
            List of pending improvements
        """
        pass
    
    @abstractmethod
    async def find_similar(
        self,
        suggestion: ImprovementSuggestion,
        threshold: float = 0.8,
    ) -> List[Improvement]:
        """
        Find improvements similar to a suggestion
        
        Args:
            suggestion: The suggestion to compare against
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of similar improvements
        """
        pass
    
    @abstractmethod
    async def get_implementation_rate(self, area: Optional[ImprovementArea] = None) -> float:
        """
        Calculate the rate of approved improvements that get implemented
        
        Args:
            area: Optional area to filter by
            
        Returns:
            Implementation rate as a percentage
        """
        pass
    
    @abstractmethod
    async def get_impact_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about improvement impacts
        
        Returns:
            Statistics including average impact, distribution, etc.
        """
        pass


class EvolutionHistoryRepository(ABC):
    """
    Repository interface for EvolutionHistory aggregate
    
    Provides persistence operations for the evolution history.
    """
    
    @abstractmethod
    async def save(self, history: EvolutionHistory) -> None:
        """
        Save the evolution history
        
        Args:
            history: The evolution history to save
        """
        pass
    
    @abstractmethod
    async def get(self) -> Optional[EvolutionHistory]:
        """
        Get the evolution history
        
        Returns:
            The evolution history if exists, None otherwise
        """
        pass
    
    @abstractmethod
    async def add_evolution(self, evolution: Evolution) -> None:
        """
        Add a completed evolution to the history
        
        Args:
            evolution: The completed evolution to add
        """
        pass
    
    @abstractmethod
    async def find_previous_improvements(
        self,
        area: ImprovementArea,
        limit: int = 10,
    ) -> List[Improvement]:
        """
        Find previous improvements in a specific area
        
        Args:
            area: The improvement area
            limit: Maximum number of results
            
        Returns:
            List of previous improvements
        """
        pass
    
    @abstractmethod
    async def check_duplicate_improvement(
        self,
        suggestion: ImprovementSuggestion,
    ) -> bool:
        """
        Check if a similar improvement has been made before
        
        Args:
            suggestion: The improvement suggestion to check
            
        Returns:
            True if duplicate exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_evolution_timeline(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get evolution timeline with key events
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Timeline of evolution events
        """
        pass
    
    @abstractmethod
    async def get_improvement_trends(
        self,
        days: int = 90,
    ) -> Dict[str, Any]:
        """
        Analyze improvement trends over time
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Trend analysis including popular areas, success rates, etc.
        """
        pass
    
    @abstractmethod
    async def update(self, history: EvolutionHistory) -> bool:
        """
        Update the evolution history
        
        Args:
            history: The evolution history to update
            
        Returns:
            True if updated, False if not found
        """
        pass


class EvolutionMetricsRepository(ABC):
    """
    Repository interface for evolution metrics and analytics
    
    Provides aggregated metrics across the evolution context.
    """
    
    @abstractmethod
    async def save_metrics_snapshot(
        self,
        evolution_id: UUID,
        metrics: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """
        Save a metrics snapshot for an evolution
        
        Args:
            evolution_id: The evolution ID
            metrics: The metrics to save
            timestamp: When the metrics were captured
        """
        pass
    
    @abstractmethod
    async def get_metrics_history(
        self,
        metric_name: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get historical values for a specific metric
        
        Args:
            metric_name: Name of the metric
            days: Number of days of history
            
        Returns:
            List of metric values with timestamps
        """
        pass
    
    @abstractmethod
    async def get_evolution_impact(
        self,
        evolution_id: UUID,
    ) -> Dict[str, Any]:
        """
        Calculate the impact of a specific evolution
        
        Args:
            evolution_id: The evolution ID
            
        Returns:
            Impact analysis including before/after metrics
        """
        pass
    
    @abstractmethod
    async def get_cumulative_improvements(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, float]:
        """
        Get cumulative improvements over a period
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Cumulative improvement percentages by metric
        """
        pass
    
    @abstractmethod
    async def identify_regression_areas(
        self,
        threshold: float = -5.0,
    ) -> List[Dict[str, Any]]:
        """
        Identify areas where metrics have regressed
        
        Args:
            threshold: Percentage decrease to consider regression
            
        Returns:
            List of regression areas with details
        """
        pass
    
    @abstractmethod
    async def get_evolution_velocity(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Calculate evolution velocity metrics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Velocity metrics including cycle time, frequency, etc.
        """
        pass
    
    @abstractmethod
    async def predict_next_evolution_areas(
        self,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Predict areas likely to need evolution next
        
        Args:
            limit: Maximum number of predictions
            
        Returns:
            Predicted evolution areas with confidence scores
        """
        pass