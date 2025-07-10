"""
Aggregates for Evolution Effectiveness Context

These aggregates enforce business rules and maintain consistency in the evolution effectiveness domain.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from .value_objects import (
    SuccessMetric, MetricMeasurement, EffectivenessScore, ValidationResult,
    EvolutionImpact, EvolutionPattern, EvolutionHealth,
    MetricType, EffectivenessLevel, ValidationStatus
)
from .events import (
    EvolutionValidated, EvolutionRolledBack, EffectivenessAssessed,
    MetricsCollected, EvolutionPatternDetected, EvolutionHealthAssessed,
    EvolutionCycleDetected, EvolutionTargetMissed, EvolutionSuccessConfirmed
)


@dataclass
class EvolutionEffectiveness:
    """
    Aggregate root for managing evolution effectiveness assessment
    
    This aggregate is responsible for tracking and validating the effectiveness
    of individual system evolutions.
    """
    
    id: UUID = field(default_factory=uuid4)
    evolution_id: str = ""
    creation_date: datetime = field(default_factory=datetime.now)
    success_metrics: Dict[str, SuccessMetric] = field(default_factory=dict)
    baseline_measurements: Dict[str, MetricMeasurement] = field(default_factory=dict)
    current_measurements: Dict[str, MetricMeasurement] = field(default_factory=dict)
    effectiveness_scores: List[EffectivenessScore] = field(default_factory=list)
    validation_results: List[ValidationResult] = field(default_factory=list)
    status: ValidationStatus = ValidationStatus.PENDING
    rollback_info: Optional[Dict] = None
    domain_events: List = field(default_factory=list)
    
    def define_success_metrics(self, metrics: List[SuccessMetric]) -> None:
        """Define the success metrics for this evolution"""
        for metric in metrics:
            self.success_metrics[metric.name] = metric
    
    def record_baseline_measurement(self, measurement: MetricMeasurement) -> None:
        """Record a baseline measurement before evolution"""
        if measurement.metric_name not in self.success_metrics:
            raise ValueError(f"Metric {measurement.metric_name} not defined")
        
        self.baseline_measurements[measurement.metric_name] = measurement
    
    def record_current_measurement(self, measurement: MetricMeasurement) -> None:
        """Record a current measurement after evolution"""
        if measurement.metric_name not in self.success_metrics:
            raise ValueError(f"Metric {measurement.metric_name} not defined")
        
        self.current_measurements[measurement.metric_name] = measurement
        
        # Emit metrics collected event
        self.domain_events.append(
            MetricsCollected(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="MetricsCollected",
                aggregate_id=self.id,
                evolution_id=self.evolution_id,
                metrics_collected={measurement.metric_name: measurement.value},
                collection_timestamp=measurement.timestamp,
                collection_method="direct_measurement"
            )
        )
    
    def calculate_effectiveness_score(self) -> EffectivenessScore:
        """Calculate the current effectiveness score"""
        if not self.baseline_measurements or not self.current_measurements:
            return EffectivenessScore(
                overall_score=0.0,
                effectiveness_level=EffectivenessLevel.INEFFECTIVE,
                metric_scores={},
                confidence=0.0,
                calculated_at=datetime.now()
            )
        
        metric_scores = {}
        weighted_scores = []
        
        for metric_name, metric in self.success_metrics.items():
            if metric_name in self.baseline_measurements and metric_name in self.current_measurements:
                baseline = self.baseline_measurements[metric_name].value
                current = self.current_measurements[metric_name].value
                
                # Calculate improvement score (0-100)
                improvement = metric.calculate_improvement(current)
                
                # Convert to 0-100 scale where meeting target = 100
                if metric.is_target_achieved(current):
                    score = 100.0
                else:
                    # Partial score based on progress toward target
                    target_improvement = metric.calculate_improvement(metric.target_value)
                    if target_improvement != 0:
                        score = max(0, min(100, (improvement / target_improvement) * 100))
                    else:
                        score = 50.0  # Neutral score if no improvement expected
                
                metric_scores[metric_name] = score
                weighted_scores.append(score * metric.weight)
        
        # Calculate overall score
        if weighted_scores:
            total_weights = sum(metric.weight for metric in self.success_metrics.values())
            overall_score = sum(weighted_scores) / total_weights if total_weights > 0 else 0.0
        else:
            overall_score = 0.0
        
        # Determine effectiveness level
        if overall_score >= 80:
            level = EffectivenessLevel.HIGHLY_EFFECTIVE
        elif overall_score >= 60:
            level = EffectivenessLevel.EFFECTIVE
        elif overall_score >= 40:
            level = EffectivenessLevel.MODERATELY_EFFECTIVE
        elif overall_score >= 20:
            level = EffectivenessLevel.INEFFECTIVE
        else:
            level = EffectivenessLevel.HARMFUL
        
        # Calculate confidence based on data completeness
        expected_metrics = len(self.success_metrics)
        actual_metrics = len(metric_scores)
        confidence = actual_metrics / expected_metrics if expected_metrics > 0 else 0.0
        
        effectiveness_score = EffectivenessScore(
            overall_score=overall_score,
            effectiveness_level=level,
            metric_scores=metric_scores,
            confidence=confidence,
            calculated_at=datetime.now()
        )
        
        self.effectiveness_scores.append(effectiveness_score)
        
        # Emit effectiveness assessed event
        self.domain_events.append(
            EffectivenessAssessed(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="EffectivenessAssessed",
                aggregate_id=self.id,
                evolution_id=self.evolution_id,
                effectiveness_score=effectiveness_score,
                assessment_method="metric_based",
                metrics_used=list(metric_scores.keys())
            )
        )
        
        return effectiveness_score
    
    def validate_evolution(self) -> ValidationResult:
        """Validate the evolution and determine if it should be rolled back"""
        effectiveness_score = self.calculate_effectiveness_score()
        
        issues_found = []
        recommendations = []
        should_rollback = False
        
        # Check if evolution is harmful
        if effectiveness_score.effectiveness_level == EffectivenessLevel.HARMFUL:
            issues_found.append("Evolution has harmful impact on system metrics")
            should_rollback = True
        
        # Check if evolution is ineffective
        if effectiveness_score.effectiveness_level == EffectivenessLevel.INEFFECTIVE:
            issues_found.append("Evolution shows no positive impact")
            recommendations.append("Consider alternative approaches")
        
        # Check if confidence is too low
        if effectiveness_score.confidence < 0.5:
            issues_found.append("Insufficient data to assess effectiveness")
            recommendations.append("Collect more metrics before validation")
        
        # Check for missed targets
        missed_targets = []
        for metric_name, metric in self.success_metrics.items():
            if metric_name in self.current_measurements:
                current_value = self.current_measurements[metric_name].value
                if not metric.is_target_achieved(current_value):
                    missed_targets.append(metric_name)
        
        if missed_targets:
            issues_found.append(f"Failed to meet targets for: {', '.join(missed_targets)}")
            
            # Emit target missed event
            self.domain_events.append(
                EvolutionTargetMissed(
                    event_id=uuid4(),
                    occurred_at=datetime.now(),
                    event_type="EvolutionTargetMissed",
                    aggregate_id=self.id,
                    evolution_id=self.evolution_id,
                    missed_targets=missed_targets,
                    actual_values={name: self.current_measurements[name].value for name in missed_targets},
                    target_values={name: self.success_metrics[name].target_value for name in missed_targets},
                    impact_assessment="negative"
                )
            )
        
        # Determine validation status
        if should_rollback:
            validation_status = ValidationStatus.FAILED
        elif effectiveness_score.is_effective():
            validation_status = ValidationStatus.VALIDATED
        else:
            validation_status = ValidationStatus.PENDING
        
        validation_result = ValidationResult(
            evolution_id=self.evolution_id,
            validation_status=validation_status,
            effectiveness_score=effectiveness_score,
            validation_timestamp=datetime.now(),
            issues_found=issues_found,
            recommendations=recommendations,
            should_rollback=should_rollback
        )
        
        self.validation_results.append(validation_result)
        self.status = validation_status
        
        # Emit validation event
        self.domain_events.append(
            EvolutionValidated(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="EvolutionValidated",
                aggregate_id=self.id,
                evolution_id=self.evolution_id,
                validation_result=validation_result,
                effectiveness_score=effectiveness_score
            )
        )
        
        return validation_result
    
    def rollback_evolution(self, reason: str, affected_components: List[str]) -> None:
        """Roll back the evolution"""
        self.status = ValidationStatus.ROLLED_BACK
        self.rollback_info = {
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "affected_components": affected_components
        }
        
        # Emit rollback event
        self.domain_events.append(
            EvolutionRolledBack(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                event_type="EvolutionRolledBack",
                aggregate_id=self.id,
                evolution_id=self.evolution_id,
                rollback_reason=reason,
                rollback_timestamp=datetime.now(),
                affected_components=affected_components
            )
        )


@dataclass
class EvolutionMetrics:
    """
    Aggregate for managing evolution metrics collection and analysis
    """
    
    id: UUID = field(default_factory=uuid4)
    evolution_id: str = ""
    metric_definitions: Dict[str, SuccessMetric] = field(default_factory=dict)
    measurements: List[MetricMeasurement] = field(default_factory=list)
    automated_collection_enabled: bool = True
    collection_frequency: int = 24  # hours
    last_collection: Optional[datetime] = None
    domain_events: List = field(default_factory=list)
    
    def add_metric_definition(self, metric: SuccessMetric) -> None:
        """Add a new metric definition"""
        self.metric_definitions[metric.name] = metric
    
    def record_measurement(self, measurement: MetricMeasurement) -> None:
        """Record a new measurement"""
        self.measurements.append(measurement)
        self.last_collection = measurement.timestamp
    
    def get_latest_measurement(self, metric_name: str) -> Optional[MetricMeasurement]:
        """Get the latest measurement for a specific metric"""
        measurements = [m for m in self.measurements if m.metric_name == metric_name]
        return max(measurements, key=lambda m: m.timestamp) if measurements else None
    
    def should_collect_metrics(self) -> bool:
        """Check if it's time to collect metrics"""
        if not self.automated_collection_enabled:
            return False
        
        if self.last_collection is None:
            return True
        
        time_since_last = datetime.now() - self.last_collection
        return time_since_last.total_seconds() >= (self.collection_frequency * 3600)


@dataclass
class EvolutionValidation:
    """
    Aggregate for managing evolution validation processes
    """
    
    id: UUID = field(default_factory=uuid4)
    validation_rules: Dict[str, callable] = field(default_factory=dict)
    validation_history: List[ValidationResult] = field(default_factory=list)
    auto_rollback_enabled: bool = True
    rollback_threshold: float = 20.0  # Effectiveness score threshold
    domain_events: List = field(default_factory=list)
    
    def add_validation_rule(self, rule_name: str, rule_function: callable) -> None:
        """Add a custom validation rule"""
        self.validation_rules[rule_name] = rule_function
    
    def validate_evolution_effectiveness(self, evolution_effectiveness: EvolutionEffectiveness) -> bool:
        """Validate an evolution's effectiveness using all rules"""
        validation_result = evolution_effectiveness.validate_evolution()
        self.validation_history.append(validation_result)
        
        # Check if auto-rollback should be triggered
        if (self.auto_rollback_enabled and 
            validation_result.effectiveness_score and
            validation_result.effectiveness_score.overall_score < self.rollback_threshold):
            
            evolution_effectiveness.rollback_evolution(
                reason="Automatic rollback due to low effectiveness score",
                affected_components=["evolution_system"]
            )
            return False
        
        return validation_result.validation_status == ValidationStatus.VALIDATED