"""
Evolution Context Domain Events

Domain events that occur within the evolution context, including system improvements,
architectural changes, and validation processes.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.events.domain_event import DomainEvent


@dataclass(frozen=True)
class EvolutionTriggered(DomainEvent):
    """Event published when system evolution is triggered"""
    
    evolution_id: UUID
    trigger_type: str
    trigger_details: Dict[str, Any]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "EvolutionTriggered")
        object.__setattr__(self, "aggregate_id", self.evolution_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "evolution_id": str(self.evolution_id),
            "trigger_type": self.trigger_type,
            "trigger_details": self.trigger_details,
        })
        return data


@dataclass(frozen=True)
class ImprovementSuggested(DomainEvent):
    """Event published when an improvement is suggested"""
    
    evolution_id: UUID
    improvement_id: UUID
    area: str
    title: str
    impact: str  # "low", "medium", "high"
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "ImprovementSuggested")
        object.__setattr__(self, "aggregate_id", self.evolution_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "evolution_id": str(self.evolution_id),
            "improvement_id": str(self.improvement_id),
            "area": self.area,
            "title": self.title,
            "impact": self.impact,
        })
        return data


@dataclass(frozen=True)
class EvolutionPlanCreated(DomainEvent):
    """Event published when an evolution plan is created"""
    
    evolution_id: UUID
    plan_steps: int
    estimated_duration_hours: float
    risk_level: str
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "EvolutionPlanCreated")
        object.__setattr__(self, "aggregate_id", self.evolution_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "evolution_id": str(self.evolution_id),
            "plan_steps": self.plan_steps,
            "estimated_duration_hours": self.estimated_duration_hours,
            "risk_level": self.risk_level,
        })
        return data


@dataclass(frozen=True)
class EvolutionApplied(DomainEvent):
    """Event published when evolution changes are applied"""
    
    evolution_id: UUID
    improvements_count: int
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "EvolutionApplied")
        object.__setattr__(self, "aggregate_id", self.evolution_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "evolution_id": str(self.evolution_id),
            "improvements_count": self.improvements_count,
        })
        return data


@dataclass(frozen=True)
class EvolutionValidated(DomainEvent):
    """Event published when evolution is validated"""
    
    evolution_id: UUID
    validation_passed: bool
    improvements_validated: int
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "EvolutionValidated")
        object.__setattr__(self, "aggregate_id", self.evolution_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "evolution_id": str(self.evolution_id),
            "validation_passed": self.validation_passed,
            "improvements_validated": self.improvements_validated,
        })
        return data


@dataclass(frozen=True)
class EvolutionCompleted(DomainEvent):
    """Event published when evolution cycle is completed"""
    
    evolution_id: UUID
    total_improvements: int
    successful_improvements: int
    metrics_improvement: float  # Percentage improvement
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "EvolutionCompleted")
        object.__setattr__(self, "aggregate_id", self.evolution_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "evolution_id": str(self.evolution_id),
            "total_improvements": self.total_improvements,
            "successful_improvements": self.successful_improvements,
            "metrics_improvement": self.metrics_improvement,
        })
        return data


@dataclass(frozen=True)
class SystemUpgraded(DomainEvent):
    """Event published when system is upgraded through evolution"""
    
    evolution_id: UUID
    version_before: str
    version_after: str
    improvements_applied: int
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "SystemUpgraded")
        object.__setattr__(self, "aggregate_id", self.evolution_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "evolution_id": str(self.evolution_id),
            "version_before": self.version_before,
            "version_after": self.version_after,
            "improvements_applied": self.improvements_applied,
        })
        return data


@dataclass(frozen=True)
class PerformanceAnalyzed(DomainEvent):
    """Event published when performance is analyzed for evolution"""
    
    evolution_id: UUID
    performance_score: float
    bottlenecks_found: List[str]
    optimization_opportunities: int
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "PerformanceAnalyzed")
        object.__setattr__(self, "aggregate_id", self.evolution_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "evolution_id": str(self.evolution_id),
            "performance_score": self.performance_score,
            "bottlenecks_found": self.bottlenecks_found,
            "optimization_opportunities": self.optimization_opportunities,
        })
        return data


@dataclass(frozen=True)
class ArchitectureAssessed(DomainEvent):
    """Event published when architecture is assessed"""
    
    evolution_id: UUID
    architecture_score: float
    issues_found: List[str]
    recommendations: List[str]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "ArchitectureAssessed")
        object.__setattr__(self, "aggregate_id", self.evolution_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "evolution_id": str(self.evolution_id),
            "architecture_score": self.architecture_score,
            "issues_found": self.issues_found,
            "recommendations": self.recommendations,
        })
        return data


@dataclass(frozen=True)
class DuplicateEvolutionDetected(DomainEvent):
    """Event published when duplicate evolution is detected"""
    
    evolution_id: UUID
    duplicate_of: UUID
    similarity_score: float
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "DuplicateEvolutionDetected")
        object.__setattr__(self, "aggregate_id", self.evolution_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "evolution_id": str(self.evolution_id),
            "duplicate_of": str(self.duplicate_of),
            "similarity_score": self.similarity_score,
        })
        return data


@dataclass(frozen=True)
class EvolutionRolledBack(DomainEvent):
    """Event published when evolution is rolled back"""
    
    evolution_id: UUID
    reason: str
    rollback_steps: List[str]
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "EvolutionRolledBack")
        object.__setattr__(self, "aggregate_id", self.evolution_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "evolution_id": str(self.evolution_id),
            "reason": self.reason,
            "rollback_steps": self.rollback_steps,
        })
        return data


@dataclass(frozen=True)
class EvolutionMetricsCollected(DomainEvent):
    """Event published when evolution metrics are collected"""
    
    evolution_id: UUID
    performance_score: float
    reliability_score: float
    maintainability_score: float
    security_score: float
    
    def __post_init__(self):
        object.__setattr__(self, "event_type", "EvolutionMetricsCollected")
        object.__setattr__(self, "aggregate_id", self.evolution_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        data = super().to_dict()
        data.update({
            "evolution_id": str(self.evolution_id),
            "performance_score": self.performance_score,
            "reliability_score": self.reliability_score,
            "maintainability_score": self.maintainability_score,
            "security_score": self.security_score,
        })
        return data