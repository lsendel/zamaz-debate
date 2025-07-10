"""
Value Objects for Evolution Effectiveness Context

These immutable objects represent concepts in the evolution effectiveness domain.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import UUID


class MetricType(Enum):
    """Types of metrics that can be collected"""
    PERFORMANCE = "performance"
    QUALITY = "quality"
    USABILITY = "usability"
    FUNCTIONALITY = "functionality"
    TECHNICAL_DEBT = "technical_debt"
    ERROR_RATE = "error_rate"
    USER_SATISFACTION = "user_satisfaction"


class EffectivenessLevel(Enum):
    """Levels of evolution effectiveness"""
    HIGHLY_EFFECTIVE = "highly_effective"
    EFFECTIVE = "effective"
    MODERATELY_EFFECTIVE = "moderately_effective"
    INEFFECTIVE = "ineffective"
    HARMFUL = "harmful"


class ValidationStatus(Enum):
    """Status of evolution validation"""
    PENDING = "pending"
    VALIDATED = "validated"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class SuccessMetric:
    """Defines a success metric for measuring evolution effectiveness"""
    metric_type: MetricType
    name: str
    description: str
    baseline_value: float
    target_value: float
    unit: str
    weight: float = 1.0  # Weight for overall effectiveness calculation
    
    def calculate_improvement(self, current_value: float) -> float:
        """Calculate improvement percentage from baseline"""
        if self.baseline_value == 0:
            return 0.0
        return ((current_value - self.baseline_value) / self.baseline_value) * 100
    
    def is_target_achieved(self, current_value: float) -> bool:
        """Check if the target value has been achieved"""
        if self.target_value > self.baseline_value:
            return current_value >= self.target_value
        else:
            return current_value <= self.target_value


@dataclass(frozen=True)
class MetricMeasurement:
    """A measurement of a specific metric at a point in time"""
    metric_name: str
    value: float
    timestamp: datetime
    context: Dict[str, Union[str, int, float]]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }


@dataclass(frozen=True)
class EffectivenessScore:
    """Represents the effectiveness score of an evolution"""
    overall_score: float  # 0-100 scale
    effectiveness_level: EffectivenessLevel
    metric_scores: Dict[str, float]
    confidence: float  # 0-1 scale
    calculated_at: datetime
    
    def is_effective(self) -> bool:
        """Check if the evolution is considered effective"""
        return self.effectiveness_level in [
            EffectivenessLevel.EFFECTIVE,
            EffectivenessLevel.HIGHLY_EFFECTIVE
        ]
    
    def requires_attention(self) -> bool:
        """Check if the evolution requires attention (low score or harmful)"""
        return self.effectiveness_level in [
            EffectivenessLevel.INEFFECTIVE,
            EffectivenessLevel.HARMFUL
        ]


@dataclass(frozen=True)
class ValidationResult:
    """Result of evolution validation"""
    evolution_id: str
    validation_status: ValidationStatus
    effectiveness_score: Optional[EffectivenessScore]
    validation_timestamp: datetime
    issues_found: List[str]
    recommendations: List[str]
    should_rollback: bool = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "evolution_id": self.evolution_id,
            "validation_status": self.validation_status.value,
            "effectiveness_score": {
                "overall_score": self.effectiveness_score.overall_score,
                "effectiveness_level": self.effectiveness_score.effectiveness_level.value,
                "metric_scores": self.effectiveness_score.metric_scores,
                "confidence": self.effectiveness_score.confidence,
                "calculated_at": self.effectiveness_score.calculated_at.isoformat()
            } if self.effectiveness_score else None,
            "validation_timestamp": self.validation_timestamp.isoformat(),
            "issues_found": self.issues_found,
            "recommendations": self.recommendations,
            "should_rollback": self.should_rollback
        }


@dataclass(frozen=True)
class EvolutionImpact:
    """Represents the measured impact of an evolution"""
    evolution_id: str
    before_metrics: Dict[str, MetricMeasurement]
    after_metrics: Dict[str, MetricMeasurement]
    impact_duration: int  # Days since evolution
    side_effects: List[str]  # Unexpected effects observed
    
    def get_metric_improvement(self, metric_name: str) -> Optional[float]:
        """Get improvement percentage for a specific metric"""
        if metric_name not in self.before_metrics or metric_name not in self.after_metrics:
            return None
        
        before = self.before_metrics[metric_name].value
        after = self.after_metrics[metric_name].value
        
        if before == 0:
            return None
        
        return ((after - before) / before) * 100


@dataclass(frozen=True)
class EvolutionPattern:
    """Represents a pattern in evolution history"""
    pattern_type: str
    description: str
    occurrences: int
    evolution_ids: List[str]
    risk_level: str  # "low", "medium", "high"
    recommendation: str
    
    def is_concerning(self) -> bool:
        """Check if this pattern is concerning"""
        return self.risk_level in ["medium", "high"] and self.occurrences >= 3


@dataclass(frozen=True)
class EvolutionHealth:
    """Overall health assessment of the evolution system"""
    effectiveness_trend: str  # "improving", "stable", "declining"
    repetition_risk: float  # 0-1 scale
    technical_debt_level: str  # "low", "medium", "high"
    diversity_score: float  # 0-1 scale
    last_effective_evolution: Optional[str]
    concerning_patterns: List[EvolutionPattern]
    
    def is_healthy(self) -> bool:
        """Check if the evolution system is healthy"""
        return (
            self.effectiveness_trend in ["improving", "stable"] and
            self.repetition_risk < 0.5 and
            self.technical_debt_level != "high" and
            self.diversity_score > 0.3
        )
    
    def get_health_score(self) -> float:
        """Get overall health score (0-100)"""
        trend_score = {"improving": 30, "stable": 20, "declining": 0}[self.effectiveness_trend]
        repetition_score = (1 - self.repetition_risk) * 25
        debt_score = {"low": 20, "medium": 10, "high": 0}[self.technical_debt_level]
        diversity_score = self.diversity_score * 25
        
        return trend_score + repetition_score + debt_score + diversity_score