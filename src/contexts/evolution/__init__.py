"""
Evolution Context

This bounded context handles system self-improvement through evolution cycles.
It manages improvement identification, planning, implementation tracking, and validation.
"""

from .aggregates import (
    Evolution,
    EvolutionHistory,
    EvolutionStatus,
    EvolutionTrigger,
    Improvement,
    ImprovementStatus,
)
from .domain_services import (
    EvolutionAnalysisService,
    EvolutionOrchestrationService,
    EvolutionPlanningService,
    EvolutionValidationService,
)
from .events import (
    ArchitectureAssessed,
    DuplicateEvolutionDetected,
    EvolutionApplied,
    EvolutionCompleted,
    EvolutionMetricsCollected,
    EvolutionPlanCreated,
    EvolutionRolledBack,
    EvolutionTriggered,
    EvolutionValidated,
    ImprovementSuggested,
    PerformanceAnalyzed,
    SystemUpgraded,
)
from .repositories import (
    EvolutionHistoryRepository,
    EvolutionMetricsRepository,
    EvolutionRepository,
    ImprovementRepository,
)
from .value_objects import (
    EvolutionImpact,
    EvolutionMetrics,
    EvolutionPlan,
    EvolutionStep,
    ImprovementArea,
    ImprovementSuggestion,
    RiskLevel,
    ValidationResult,
)


class EvolutionContext:
    """Main context class for Evolution"""
    pass


__all__ = [
    "EvolutionContext",
    # Aggregates
    "Evolution",
    "Improvement",
    "EvolutionHistory",
    "EvolutionStatus",
    "ImprovementStatus",
    "EvolutionTrigger",
    # Value Objects
    "ImprovementSuggestion",
    "ImprovementArea",
    "EvolutionPlan",
    "EvolutionStep",
    "RiskLevel",
    "ValidationResult",
    "EvolutionMetrics",
    "EvolutionImpact",
    # Events
    "EvolutionTriggered",
    "ImprovementSuggested",
    "EvolutionPlanCreated",
    "EvolutionApplied",
    "EvolutionValidated",
    "EvolutionCompleted",
    "SystemUpgraded",
    "PerformanceAnalyzed",
    "ArchitectureAssessed",
    "DuplicateEvolutionDetected",
    "EvolutionRolledBack",
    "EvolutionMetricsCollected",
    # Repositories
    "EvolutionRepository",
    "ImprovementRepository",
    "EvolutionHistoryRepository",
    "EvolutionMetricsRepository",
    # Domain Services
    "EvolutionAnalysisService",
    "EvolutionPlanningService",
    "EvolutionValidationService",
    "EvolutionOrchestrationService",
]
