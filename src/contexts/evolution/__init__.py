"""
Evolution Context

This bounded context handles system evolution and self-improvement.
It manages evolution cycles, improvements, and system upgrades.
"""

from .aggregates import EvolutionCycle, Improvement
from .domain_services import EvolutionStrategy, DuplicationPrevention
from .value_objects import EvolutionPlan, ImprovementSuggestion
from .repositories import EvolutionRepository, ImprovementRepository
from .events import EvolutionTriggered, ImprovementSuggested, EvolutionApplied

__all__ = [
    'EvolutionCycle',
    'Improvement',
    'EvolutionStrategy',
    'DuplicationPrevention',
    'EvolutionPlan',
    'ImprovementSuggestion',
    'EvolutionRepository',
    'ImprovementRepository',
    'EvolutionTriggered',
    'ImprovementSuggested',
    'EvolutionApplied'
]