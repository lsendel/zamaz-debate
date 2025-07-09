"""
Evolution Context

This bounded context handles system evolution and self-improvement.
It manages evolution cycles, improvements, and system upgrades.
"""

from .aggregates import EvolutionCycle, Improvement
from .domain_services import DuplicationPrevention, EvolutionStrategy
from .events import EvolutionApplied, EvolutionTriggered, ImprovementSuggested
from .repositories import EvolutionRepository, ImprovementRepository
from .value_objects import EvolutionPlan, ImprovementSuggestion

__all__ = [
    "EvolutionCycle",
    "Improvement",
    "EvolutionStrategy",
    "DuplicationPrevention",
    "EvolutionPlan",
    "ImprovementSuggestion",
    "EvolutionRepository",
    "ImprovementRepository",
    "EvolutionTriggered",
    "ImprovementSuggested",
    "EvolutionApplied",
]
