"""
Evolution Context Aggregates

This module contains the aggregate roots for the evolution context.
Aggregates manage system self-improvement, architectural evolution, and improvement tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from .events import (
    EvolutionApplied,
    EvolutionCompleted,
    EvolutionPlanCreated,
    EvolutionTriggered,
    EvolutionValidated,
    ImprovementSuggested,
    SystemUpgraded,
)
from .value_objects import (
    EvolutionMetrics,
    EvolutionPlan,
    ImprovementArea,
    ImprovementSuggestion,
    ValidationResult,
)


class EvolutionStatus(Enum):
    """Status of an evolution cycle"""
    
    TRIGGERED = "triggered"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ImprovementStatus(Enum):
    """Status of an improvement suggestion"""
    
    SUGGESTED = "suggested"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    VALIDATED = "validated"


class EvolutionTrigger(Enum):
    """What triggered the evolution"""
    
    SCHEDULED = "scheduled"
    PERFORMANCE = "performance"
    ERROR_RATE = "error_rate"
    MANUAL = "manual"
    ARCHITECTURAL = "architectural"
    SECURITY = "security"


@dataclass
class Evolution:
    """
    Evolution Aggregate Root
    
    Manages the lifecycle of a system evolution cycle from trigger to completion.
    Ensures that evolutions are properly validated and don't duplicate previous improvements.
    """
    
    id: UUID = field(default_factory=uuid4)
    trigger: EvolutionTrigger = EvolutionTrigger.MANUAL
    trigger_details: Dict[str, Any] = field(default_factory=dict)
    status: EvolutionStatus = EvolutionStatus.TRIGGERED
    plan: Optional[EvolutionPlan] = None
    improvements: List["Improvement"] = field(default_factory=list)
    metrics_before: Optional[EvolutionMetrics] = None
    metrics_after: Optional[EvolutionMetrics] = None
    validation_result: Optional[ValidationResult] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    
    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    
    def __post_init__(self):
        """Initialize evolution and publish domain event"""
        if self.status == EvolutionStatus.TRIGGERED and not self._events:
            self._publish_event(
                EvolutionTriggered(
                    evolution_id=self.id,
                    trigger_type=self.trigger.value,
                    trigger_details=self.trigger_details,
                    occurred_at=datetime.now(),
                )
            )
    
    def start_analysis(self, current_metrics: EvolutionMetrics) -> None:
        """Start analyzing the system for improvements"""
        if self.status != EvolutionStatus.TRIGGERED:
            raise ValueError("Evolution must be in triggered state to start analysis")
        
        self.status = EvolutionStatus.ANALYZING
        self.started_at = datetime.now()
        self.metrics_before = current_metrics
    
    def suggest_improvement(self, improvement: "Improvement") -> None:
        """Add an improvement suggestion"""
        if self.status not in [EvolutionStatus.ANALYZING, EvolutionStatus.PLANNING]:
            raise ValueError("Can only suggest improvements during analysis or planning")
        
        # Check for duplicates
        if any(i.suggestion.area == improvement.suggestion.area and 
               i.suggestion.title == improvement.suggestion.title 
               for i in self.improvements):
            raise ValueError("Duplicate improvement suggestion")
        
        self.improvements.append(improvement)
        
        self._publish_event(
            ImprovementSuggested(
                evolution_id=self.id,
                improvement_id=improvement.id,
                area=improvement.suggestion.area.value,
                title=improvement.suggestion.title,
                impact=improvement.suggestion.estimated_impact,
                occurred_at=datetime.now(),
            )
        )
    
    def create_plan(self, plan: EvolutionPlan) -> None:
        """Create an evolution plan from approved improvements"""
        if self.status != EvolutionStatus.ANALYZING:
            raise ValueError("Must be in analyzing state to create plan")
        
        # Ensure at least one improvement is approved
        approved_improvements = [i for i in self.improvements if i.is_approved]
        if not approved_improvements:
            raise ValueError("No approved improvements to plan")
        
        self.plan = plan
        self.status = EvolutionStatus.PLANNING
        
        self._publish_event(
            EvolutionPlanCreated(
                evolution_id=self.id,
                plan_steps=len(plan.steps),
                estimated_duration_hours=plan.estimated_duration_hours,
                risk_level=plan.risk_level,
                occurred_at=datetime.now(),
            )
        )
    
    def start_implementation(self) -> None:
        """Start implementing the evolution plan"""
        if self.status != EvolutionStatus.PLANNING:
            raise ValueError("Must have a plan to start implementation")
        
        if not self.plan:
            raise ValueError("No evolution plan exists")
        
        self.status = EvolutionStatus.IMPLEMENTING
        
        self._publish_event(
            EvolutionApplied(
                evolution_id=self.id,
                improvements_count=len([i for i in self.improvements if i.is_approved]),
                occurred_at=datetime.now(),
            )
        )
    
    def complete_implementation(self) -> None:
        """Mark implementation as complete and ready for validation"""
        if self.status != EvolutionStatus.IMPLEMENTING:
            raise ValueError("Must be implementing to complete")
        
        self.status = EvolutionStatus.VALIDATING
    
    def validate(self, validation_result: ValidationResult, current_metrics: EvolutionMetrics) -> None:
        """Validate the evolution results"""
        if self.status != EvolutionStatus.VALIDATING:
            raise ValueError("Must be in validating state")
        
        self.validation_result = validation_result
        self.metrics_after = current_metrics
        
        if validation_result.is_successful:
            self.status = EvolutionStatus.COMPLETED
            self.completed_at = datetime.now()
            
            # Mark improvements as validated
            for improvement in self.improvements:
                if improvement.is_approved:
                    improvement.mark_validated()
            
            self._publish_event(
                EvolutionValidated(
                    evolution_id=self.id,
                    validation_passed=True,
                    improvements_validated=len([i for i in self.improvements if i.is_validated]),
                    occurred_at=datetime.now(),
                )
            )
            
            self._publish_event(
                EvolutionCompleted(
                    evolution_id=self.id,
                    total_improvements=len(self.improvements),
                    successful_improvements=len([i for i in self.improvements if i.is_validated]),
                    metrics_improvement=self._calculate_improvement(),
                    occurred_at=datetime.now(),
                )
            )
        else:
            self.status = EvolutionStatus.FAILED
            self._publish_event(
                EvolutionValidated(
                    evolution_id=self.id,
                    validation_passed=False,
                    improvements_validated=0,
                    occurred_at=datetime.now(),
                )
            )
    
    def rollback(self, reason: str) -> None:
        """Rollback the evolution"""
        if self.status not in [EvolutionStatus.IMPLEMENTING, EvolutionStatus.VALIDATING, EvolutionStatus.FAILED]:
            raise ValueError("Can only rollback during or after implementation")
        
        self.status = EvolutionStatus.ROLLED_BACK
        self.rolled_back_at = datetime.now()
        
        # Store rollback reason in trigger details
        self.trigger_details["rollback_reason"] = reason
    
    def _calculate_improvement(self) -> float:
        """Calculate overall improvement percentage"""
        if not self.metrics_before or not self.metrics_after:
            return 0.0
        
        # Simple average of metric improvements
        improvements = []
        
        if self.metrics_before.performance_score > 0:
            perf_improvement = ((self.metrics_after.performance_score - self.metrics_before.performance_score) 
                               / self.metrics_before.performance_score) * 100
            improvements.append(perf_improvement)
        
        if self.metrics_before.reliability_score > 0:
            rel_improvement = ((self.metrics_after.reliability_score - self.metrics_before.reliability_score) 
                              / self.metrics_before.reliability_score) * 100
            improvements.append(rel_improvement)
        
        if self.metrics_before.maintainability_score > 0:
            maint_improvement = ((self.metrics_after.maintainability_score - self.metrics_before.maintainability_score) 
                                / self.metrics_before.maintainability_score) * 100
            improvements.append(maint_improvement)
        
        return sum(improvements) / len(improvements) if improvements else 0.0
    
    def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish a domain event"""
        self._events.append(event)
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all domain events and clear the event list"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    @property
    def is_completed(self) -> bool:
        """Check if evolution is completed"""
        return self.status == EvolutionStatus.COMPLETED
    
    @property
    def is_successful(self) -> bool:
        """Check if evolution was successful"""
        return self.is_completed and self.validation_result and self.validation_result.is_successful
    
    @property
    def duration_hours(self) -> Optional[float]:
        """Calculate evolution duration in hours"""
        if self.started_at and (self.completed_at or self.rolled_back_at):
            end_time = self.completed_at or self.rolled_back_at
            duration = end_time - self.started_at
            return duration.total_seconds() / 3600
        return None


@dataclass
class Improvement:
    """
    Improvement Entity
    
    Part of the Evolution aggregate.
    Represents a single improvement suggestion within an evolution cycle.
    """
    
    id: UUID = field(default_factory=uuid4)
    evolution_id: UUID = field(default_factory=uuid4)
    suggestion: ImprovementSuggestion = field(default_factory=ImprovementSuggestion)
    status: ImprovementStatus = ImprovementStatus.SUGGESTED
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    implementation_task_id: Optional[UUID] = None
    validation_notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def approve(self, approver: str) -> None:
        """Approve the improvement for implementation"""
        if self.status != ImprovementStatus.SUGGESTED:
            raise ValueError("Can only approve suggested improvements")
        
        self.status = ImprovementStatus.APPROVED
        self.approved_by = approver
        self.approved_at = datetime.now()
    
    def reject(self, reason: str) -> None:
        """Reject the improvement"""
        if self.status != ImprovementStatus.SUGGESTED:
            raise ValueError("Can only reject suggested improvements")
        
        self.status = ImprovementStatus.REJECTED
        self.validation_notes = reason
    
    def mark_implemented(self, task_id: UUID) -> None:
        """Mark improvement as implemented"""
        if self.status != ImprovementStatus.APPROVED:
            raise ValueError("Can only implement approved improvements")
        
        self.status = ImprovementStatus.IMPLEMENTED
        self.implementation_task_id = task_id
    
    def mark_validated(self, notes: Optional[str] = None) -> None:
        """Mark improvement as validated"""
        if self.status != ImprovementStatus.IMPLEMENTED:
            raise ValueError("Can only validate implemented improvements")
        
        self.status = ImprovementStatus.VALIDATED
        if notes:
            self.validation_notes = notes
    
    @property
    def is_approved(self) -> bool:
        """Check if improvement is approved"""
        return self.status in [ImprovementStatus.APPROVED, ImprovementStatus.IMPLEMENTED, ImprovementStatus.VALIDATED]
    
    @property
    def is_implemented(self) -> bool:
        """Check if improvement is implemented"""
        return self.status in [ImprovementStatus.IMPLEMENTED, ImprovementStatus.VALIDATED]
    
    @property
    def is_validated(self) -> bool:
        """Check if improvement is validated"""
        return self.status == ImprovementStatus.VALIDATED


@dataclass
class EvolutionHistory:
    """
    Evolution History Aggregate Root
    
    Maintains the history of all system evolutions to prevent duplicate improvements
    and track long-term system evolution patterns.
    """
    
    id: UUID = field(default_factory=uuid4)
    evolutions: List[Evolution] = field(default_factory=list)
    total_improvements: int = 0
    successful_improvements: int = 0
    failed_evolutions: int = 0
    last_evolution_at: Optional[datetime] = None
    
    # Domain events
    _events: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    
    def add_evolution(self, evolution: Evolution) -> None:
        """Add a completed evolution to history"""
        if not evolution.is_completed and evolution.status != EvolutionStatus.FAILED:
            raise ValueError("Can only add completed or failed evolutions to history")
        
        self.evolutions.append(evolution)
        self.last_evolution_at = evolution.completed_at or evolution.created_at
        
        # Update statistics
        self.total_improvements += len(evolution.improvements)
        if evolution.is_successful:
            self.successful_improvements += len([i for i in evolution.improvements if i.is_validated])
        else:
            self.failed_evolutions += 1
        
        if evolution.is_successful:
            self._publish_event(
                SystemUpgraded(
                    evolution_id=evolution.id,
                    version_before="",  # Would be tracked in real implementation
                    version_after="",   # Would be tracked in real implementation
                    improvements_applied=len([i for i in evolution.improvements if i.is_validated]),
                    occurred_at=datetime.now(),
                )
            )
    
    def has_similar_improvement(self, suggestion: ImprovementSuggestion) -> bool:
        """Check if a similar improvement has been made before"""
        for evolution in self.evolutions:
            for improvement in evolution.improvements:
                if (improvement.suggestion.area == suggestion.area and
                    improvement.suggestion.title == suggestion.title and
                    improvement.is_validated):
                    return True
        return False
    
    def get_improvements_by_area(self, area: ImprovementArea) -> List[Improvement]:
        """Get all improvements for a specific area"""
        improvements = []
        for evolution in self.evolutions:
            for improvement in evolution.improvements:
                if improvement.suggestion.area == area:
                    improvements.append(improvement)
        return improvements
    
    def get_success_rate(self) -> float:
        """Calculate evolution success rate"""
        total_evolutions = len(self.evolutions)
        if total_evolutions == 0:
            return 0.0
        
        successful_evolutions = len([e for e in self.evolutions if e.is_successful])
        return (successful_evolutions / total_evolutions) * 100
    
    def get_recent_evolutions(self, days: int = 30) -> List[Evolution]:
        """Get evolutions from the last N days"""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        return [
            e for e in self.evolutions
            if e.created_at.timestamp() > cutoff_date
        ]
    
    def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish a domain event"""
        self._events.append(event)
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all domain events and clear the event list"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    @property
    def average_improvements_per_evolution(self) -> float:
        """Calculate average number of improvements per evolution"""
        if not self.evolutions:
            return 0.0
        return self.total_improvements / len(self.evolutions)
    
    @property
    def improvement_success_rate(self) -> float:
        """Calculate improvement success rate"""
        if self.total_improvements == 0:
            return 0.0
        return (self.successful_improvements / self.total_improvements) * 100