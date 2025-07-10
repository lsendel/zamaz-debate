"""
Domain Services for Evolution Effectiveness Context

These services handle complex business logic that spans multiple aggregates or
requires coordination between different parts of the system.
"""

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from .aggregates import EvolutionEffectiveness, EvolutionMetrics, EvolutionValidation
from .value_objects import (
    SuccessMetric, MetricMeasurement, EffectivenessScore, ValidationResult,
    EvolutionImpact, EvolutionPattern, EvolutionHealth,
    MetricType, EffectivenessLevel, ValidationStatus
)
from .events import (
    EvolutionPatternDetected, EvolutionHealthAssessed, EvolutionCycleDetected,
    EvolutionEffectivenessReportGenerated
)


class EvolutionEffectivenessService:
    """
    Service for managing overall evolution effectiveness assessment
    
    This service coordinates the assessment of evolution effectiveness across
    the entire system and provides insights into system health.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.evolutions_dir = self.data_dir / "evolutions"
        self.effectiveness_dir = self.data_dir / "effectiveness"
        self.effectiveness_dir.mkdir(parents=True, exist_ok=True)
    
    async def assess_evolution_effectiveness(self, evolution_id: str) -> EvolutionEffectiveness:
        """Assess the effectiveness of a specific evolution"""
        evolution_effectiveness = EvolutionEffectiveness(evolution_id=evolution_id)
        
        # Define default success metrics
        default_metrics = self._get_default_success_metrics()
        evolution_effectiveness.define_success_metrics(default_metrics)
        
        # Collect baseline and current measurements
        await self._collect_system_metrics(evolution_effectiveness)
        
        # Calculate effectiveness score
        evolution_effectiveness.calculate_effectiveness_score()
        
        # Validate evolution
        evolution_effectiveness.validate_evolution()
        
        return evolution_effectiveness
    
    def _get_default_success_metrics(self) -> List[SuccessMetric]:
        """Get default success metrics for evolution assessment"""
        return [
            SuccessMetric(
                metric_type=MetricType.PERFORMANCE,
                name="debate_completion_rate",
                description="Percentage of debates that complete successfully",
                baseline_value=80.0,
                target_value=90.0,
                unit="percentage",
                weight=2.0
            ),
            SuccessMetric(
                metric_type=MetricType.PERFORMANCE,
                name="average_response_time",
                description="Average time for AI responses",
                baseline_value=5.0,
                target_value=3.0,
                unit="seconds",
                weight=1.5
            ),
            SuccessMetric(
                metric_type=MetricType.QUALITY,
                name="code_quality_score",
                description="Overall code quality assessment",
                baseline_value=70.0,
                target_value=80.0,
                unit="score",
                weight=1.0
            ),
            SuccessMetric(
                metric_type=MetricType.ERROR_RATE,
                name="system_error_rate",
                description="Rate of system errors",
                baseline_value=5.0,
                target_value=2.0,
                unit="percentage",
                weight=2.0
            ),
            SuccessMetric(
                metric_type=MetricType.FUNCTIONALITY,
                name="feature_usage_rate",
                description="Rate of feature utilization",
                baseline_value=60.0,
                target_value=75.0,
                unit="percentage",
                weight=1.0
            )
        ]
    
    async def _collect_system_metrics(self, evolution_effectiveness: EvolutionEffectiveness) -> None:
        """Collect system metrics for effectiveness assessment"""
        # This would typically integrate with monitoring systems
        # For now, we'll simulate with file-based data
        
        current_time = datetime.now()
        
        # Simulate metric collection
        metrics = {
            "debate_completion_rate": 85.0,
            "average_response_time": 4.2,
            "code_quality_score": 75.0,
            "system_error_rate": 3.5,
            "feature_usage_rate": 68.0
        }
        
        for metric_name, value in metrics.items():
            measurement = MetricMeasurement(
                metric_name=metric_name,
                value=value,
                timestamp=current_time,
                context={"source": "system_monitor", "evolution_id": evolution_effectiveness.evolution_id}
            )
            evolution_effectiveness.record_current_measurement(measurement)
    
    async def detect_evolution_patterns(self, evolution_history: List[Dict]) -> List[EvolutionPattern]:
        """Detect concerning patterns in evolution history"""
        patterns = []
        
        # Detect repetitive feature patterns
        feature_counts = defaultdict(list)
        for evolution in evolution_history:
            feature = evolution.get("feature", "unknown")
            feature_counts[feature].append(evolution.get("id", ""))
        
        # Check for repetitive patterns
        for feature, evolution_ids in feature_counts.items():
            if len(evolution_ids) >= 3:
                risk_level = "high" if len(evolution_ids) >= 5 else "medium"
                patterns.append(
                    EvolutionPattern(
                        pattern_type="repetitive_feature",
                        description=f"Repetitive evolution pattern detected for feature: {feature}",
                        occurrences=len(evolution_ids),
                        evolution_ids=evolution_ids,
                        risk_level=risk_level,
                        recommendation=f"Stop creating {feature} evolutions until effectiveness is validated"
                    )
                )
        
        # Detect lack of diversity
        recent_evolutions = evolution_history[-10:] if len(evolution_history) > 10 else evolution_history
        unique_features = set(evo.get("feature", "") for evo in recent_evolutions)
        
        if len(unique_features) < 3 and len(recent_evolutions) > 5:
            patterns.append(
                EvolutionPattern(
                    pattern_type="low_diversity",
                    description="Low diversity in recent evolutions",
                    occurrences=len(recent_evolutions),
                    evolution_ids=[evo.get("id", "") for evo in recent_evolutions],
                    risk_level="medium",
                    recommendation="Diversify evolution types and features"
                )
            )
        
        return patterns
    
    async def assess_evolution_health(self, evolution_history: List[Dict]) -> EvolutionHealth:
        """Assess the overall health of the evolution system"""
        if not evolution_history:
            return EvolutionHealth(
                effectiveness_trend="stable",
                repetition_risk=0.0,
                technical_debt_level="low",
                diversity_score=1.0,
                last_effective_evolution=None,
                concerning_patterns=[]
            )
        
        # Analyze effectiveness trend
        recent_evolutions = evolution_history[-10:]
        effectiveness_trend = self._analyze_effectiveness_trend(recent_evolutions)
        
        # Calculate repetition risk
        repetition_risk = self._calculate_repetition_risk(evolution_history)
        
        # Assess technical debt level
        technical_debt_level = self._assess_technical_debt_level(evolution_history)
        
        # Calculate diversity score
        diversity_score = self._calculate_diversity_score(evolution_history)
        
        # Find last effective evolution
        last_effective_evolution = self._find_last_effective_evolution(evolution_history)
        
        # Detect concerning patterns
        concerning_patterns = await self.detect_evolution_patterns(evolution_history)
        
        return EvolutionHealth(
            effectiveness_trend=effectiveness_trend,
            repetition_risk=repetition_risk,
            technical_debt_level=technical_debt_level,
            diversity_score=diversity_score,
            last_effective_evolution=last_effective_evolution,
            concerning_patterns=concerning_patterns
        )
    
    def _analyze_effectiveness_trend(self, recent_evolutions: List[Dict]) -> str:
        """Analyze the trend in evolution effectiveness"""
        if len(recent_evolutions) < 3:
            return "stable"
        
        # Check for improvement patterns
        feature_types = [evo.get("type", "") for evo in recent_evolutions]
        
        # If we see variety in types, it's improving
        if len(set(feature_types)) > 2:
            return "improving"
        
        # If we see repetition, it's declining
        if len(set(feature_types)) == 1:
            return "declining"
        
        return "stable"
    
    def _calculate_repetition_risk(self, evolution_history: List[Dict]) -> float:
        """Calculate the risk of repetitive evolution patterns"""
        if len(evolution_history) < 5:
            return 0.0
        
        recent_evolutions = evolution_history[-10:]
        feature_counts = defaultdict(int)
        
        for evolution in recent_evolutions:
            feature = evolution.get("feature", "unknown")
            feature_counts[feature] += 1
        
        # Calculate risk based on repetition
        max_repetitions = max(feature_counts.values())
        total_evolutions = len(recent_evolutions)
        
        return min(1.0, max_repetitions / total_evolutions)
    
    def _assess_technical_debt_level(self, evolution_history: List[Dict]) -> str:
        """Assess the technical debt level based on evolution patterns"""
        if len(evolution_history) < 10:
            return "low"
        
        # Count feature vs refactor/fix evolutions
        feature_count = sum(1 for evo in evolution_history if evo.get("type") == "feature")
        refactor_count = sum(1 for evo in evolution_history if evo.get("type") in ["refactor", "fix", "enhancement"])
        
        total_evolutions = len(evolution_history)
        feature_ratio = feature_count / total_evolutions
        
        if feature_ratio > 0.9:
            return "high"
        elif feature_ratio > 0.7:
            return "medium"
        else:
            return "low"
    
    def _calculate_diversity_score(self, evolution_history: List[Dict]) -> float:
        """Calculate diversity score for evolution history"""
        if not evolution_history:
            return 1.0
        
        # Calculate feature diversity
        features = [evo.get("feature", "") for evo in evolution_history]
        unique_features = set(features)
        
        # Calculate type diversity
        types = [evo.get("type", "") for evo in evolution_history]
        unique_types = set(types)
        
        # Combine diversity metrics
        feature_diversity = len(unique_features) / len(features) if features else 0
        type_diversity = len(unique_types) / len(types) if types else 0
        
        return (feature_diversity + type_diversity) / 2
    
    def _find_last_effective_evolution(self, evolution_history: List[Dict]) -> Optional[str]:
        """Find the last effective evolution"""
        # This would typically check effectiveness scores
        # For now, return the most recent non-repetitive evolution
        
        recent_evolutions = evolution_history[-10:]
        feature_counts = defaultdict(int)
        
        for evolution in reversed(recent_evolutions):
            feature = evolution.get("feature", "")
            feature_counts[feature] += 1
            
            # If this is the first occurrence of this feature, it might be effective
            if feature_counts[feature] == 1:
                return evolution.get("id")
        
        return None


class MetricsCollectionService:
    """
    Service for collecting and managing evolution metrics
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.metrics_dir = self.data_dir / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
    
    async def collect_system_metrics(self, evolution_id: str) -> Dict[str, float]:
        """Collect current system metrics"""
        metrics = {}
        
        # Collect performance metrics
        metrics.update(await self._collect_performance_metrics())
        
        # Collect quality metrics
        metrics.update(await self._collect_quality_metrics())
        
        # Collect usage metrics
        metrics.update(await self._collect_usage_metrics())
        
        # Save metrics
        await self._save_metrics(evolution_id, metrics)
        
        return metrics
    
    async def _collect_performance_metrics(self) -> Dict[str, float]:
        """Collect performance-related metrics"""
        # This would typically integrate with APM tools
        # For now, simulate with file-based analysis
        
        debates_dir = self.data_dir / "debates"
        if not debates_dir.exists():
            return {"debate_completion_rate": 0.0, "average_response_time": 0.0}
        
        debate_files = list(debates_dir.glob("*.json"))
        if not debate_files:
            return {"debate_completion_rate": 0.0, "average_response_time": 0.0}
        
        completed_debates = 0
        total_response_time = 0
        total_debates = len(debate_files)
        
        for debate_file in debate_files:
            try:
                with open(debate_file, 'r') as f:
                    debate_data = json.load(f)
                
                if debate_data.get("final_decision"):
                    completed_debates += 1
                
                # Calculate response time (simplified)
                start_time = datetime.fromisoformat(debate_data.get("start_time", ""))
                end_time = datetime.fromisoformat(debate_data.get("end_time", ""))
                response_time = (end_time - start_time).total_seconds()
                total_response_time += response_time
                
            except Exception:
                continue
        
        completion_rate = (completed_debates / total_debates) * 100 if total_debates > 0 else 0
        average_response_time = total_response_time / total_debates if total_debates > 0 else 0
        
        return {
            "debate_completion_rate": completion_rate,
            "average_response_time": average_response_time
        }
    
    async def _collect_quality_metrics(self) -> Dict[str, float]:
        """Collect code quality metrics"""
        # This would typically integrate with code analysis tools
        # For now, provide simulated metrics
        
        return {
            "code_quality_score": 75.0,
            "test_coverage": 65.0,
            "technical_debt_ratio": 15.0
        }
    
    async def _collect_usage_metrics(self) -> Dict[str, float]:
        """Collect usage metrics"""
        # This would typically integrate with analytics tools
        # For now, analyze file-based data
        
        decisions_dir = self.data_dir / "decisions"
        if not decisions_dir.exists():
            return {"feature_usage_rate": 0.0, "system_error_rate": 0.0}
        
        decision_files = list(decisions_dir.glob("*.json"))
        total_decisions = len(decision_files)
        
        # Calculate feature usage rate (simplified)
        feature_usage_rate = min(100.0, total_decisions * 2.5)  # Simplified calculation
        
        # Calculate error rate (simplified)
        system_error_rate = max(0.0, 10.0 - (total_decisions * 0.05))  # Simplified calculation
        
        return {
            "feature_usage_rate": feature_usage_rate,
            "system_error_rate": system_error_rate
        }
    
    async def _save_metrics(self, evolution_id: str, metrics: Dict[str, float]) -> None:
        """Save collected metrics to file"""
        metrics_file = self.metrics_dir / f"metrics_{evolution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        metrics_data = {
            "evolution_id": evolution_id,
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        }
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)