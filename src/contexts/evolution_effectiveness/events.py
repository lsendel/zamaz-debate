"""
Domain Events for Evolution Effectiveness Context

These events represent significant occurrences in the evolution effectiveness domain.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from src.events.domain_event import DomainEvent
from .value_objects import EffectivenessScore, ValidationResult, EvolutionHealth


@dataclass(frozen=True)
class EvolutionEffectivenessEvent(DomainEvent):
    """Base event for evolution effectiveness events"""
    pass


@dataclass(frozen=True)
class EvolutionValidated(EvolutionEffectivenessEvent):
    """Event raised when an evolution has been validated"""
    evolution_id: str
    validation_result: ValidationResult
    effectiveness_score: EffectivenessScore
    
    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class EvolutionRolledBack(EvolutionEffectivenessEvent):
    """Event raised when an evolution has been rolled back"""
    evolution_id: str
    rollback_reason: str
    rollback_timestamp: datetime
    affected_components: List[str]
    
    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class EffectivenessAssessed(EvolutionEffectivenessEvent):
    """Event raised when evolution effectiveness has been assessed"""
    evolution_id: str
    effectiveness_score: EffectivenessScore
    assessment_method: str
    metrics_used: List[str]
    
    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class MetricsCollected(EvolutionEffectivenessEvent):
    """Event raised when metrics have been collected"""
    evolution_id: str
    metrics_collected: Dict[str, float]
    collection_timestamp: datetime
    collection_method: str
    
    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class EvolutionPatternDetected(EvolutionEffectivenessEvent):
    """Event raised when a concerning evolution pattern is detected"""
    pattern_type: str
    pattern_description: str
    evolution_ids: List[str]
    risk_level: str
    recommendation: str
    
    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class EvolutionHealthAssessed(EvolutionEffectivenessEvent):
    """Event raised when overall evolution health has been assessed"""
    health_assessment: EvolutionHealth
    assessment_timestamp: datetime
    previous_health_score: Optional[float]
    health_trend: str
    
    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class EvolutionCycleDetected(EvolutionEffectivenessEvent):
    """Event raised when a repetitive evolution cycle is detected"""
    cycle_pattern: str
    cycle_length: int
    evolution_ids_in_cycle: List[str]
    cycle_start_date: datetime
    intervention_recommended: bool
    
    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class EvolutionEffectivenessReportGenerated(EvolutionEffectivenessEvent):
    """Event raised when an effectiveness report has been generated"""
    report_id: str
    report_type: str
    evolution_ids_analyzed: List[str]
    report_timestamp: datetime
    key_findings: List[str]
    recommendations: List[str]
    
    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class EvolutionTargetMissed(EvolutionEffectivenessEvent):
    """Event raised when an evolution fails to meet its targets"""
    evolution_id: str
    missed_targets: List[str]
    actual_values: Dict[str, float]
    target_values: Dict[str, float]
    impact_assessment: str
    
    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class EvolutionSuccessConfirmed(EvolutionEffectivenessEvent):
    """Event raised when an evolution's success has been confirmed"""
    evolution_id: str
    success_metrics: Dict[str, float]
    success_timestamp: datetime
    impact_summary: str
    lessons_learned: List[str]
    
    def __post_init__(self):
        super().__post_init__()