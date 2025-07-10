#!/usr/bin/env python3
"""
Evolution Guidance System for Zamaz Debate System

This system addresses the critical gap between evolution tracking and debate generation.
It prevents repetitive evolution loops and ensures evolution effectiveness.

Key Features:
- Pre-debate validation to prevent repetitive improvements
- Evolution effectiveness measurement  
- Intelligent suggestion of diverse improvement areas
- Integration with existing EvolutionTracker
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .evolution_tracker import EvolutionTracker


@dataclass
class EvolutionMetrics:
    """Metrics to measure evolution effectiveness"""
    debate_count: int
    decision_count: int
    error_rate: float
    performance_score: float
    user_satisfaction: float
    system_stability: float
    timestamp: datetime


@dataclass
class EvolutionGuidanceResult:
    """Result of evolution guidance analysis"""
    should_evolve: bool
    recommended_area: Optional[str]
    reason: str
    suggested_question: Optional[str]
    blocked_reason: Optional[str]
    alternative_suggestions: List[str]


class EvolutionGuidanceSystem:
    """
    System that guides evolution decisions to prevent loops and ensure effectiveness.
    
    This is the missing piece that integrates evolution tracking with debate generation
    to solve the performance optimization repetition crisis.
    """
    
    def __init__(self, evolution_tracker: EvolutionTracker = None, metrics_dir: str = None):
        self.evolution_tracker = evolution_tracker or EvolutionTracker()
        
        if metrics_dir is None:
            metrics_dir = Path(__file__).parent.parent.parent / "data" / "evolution_metrics"
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.metrics_dir / "evolution_effectiveness.json"
        
        # Load historical metrics
        self.metrics_history = self._load_metrics_history()
        
        # Configuration for guidance rules
        self.repetition_threshold = 3  # Max same feature type in recent evolutions
        self.effectiveness_threshold = 0.1  # Min improvement required to continue
        self.cooldown_hours = 24  # Hours to wait after failed evolution
        
    def _load_metrics_history(self) -> List[EvolutionMetrics]:
        """Load historical evolution metrics"""
        if not self.metrics_file.exists():
            return []
            
        try:
            with open(self.metrics_file, 'r') as f:
                data = json.load(f)
                return [
                    EvolutionMetrics(
                        debate_count=m['debate_count'],
                        decision_count=m['decision_count'],
                        error_rate=m['error_rate'],
                        performance_score=m['performance_score'],
                        user_satisfaction=m['user_satisfaction'],
                        system_stability=m['system_stability'],
                        timestamp=datetime.fromisoformat(m['timestamp'])
                    )
                    for m in data
                ]
        except Exception as e:
            print(f"Warning: Could not load metrics history: {e}")
            return []
    
    def _save_metrics_history(self):
        """Save metrics history to file"""
        try:
            data = [
                {
                    'debate_count': m.debate_count,
                    'decision_count': m.decision_count,
                    'error_rate': m.error_rate,
                    'performance_score': m.performance_score,
                    'user_satisfaction': m.user_satisfaction,
                    'system_stability': m.system_stability,
                    'timestamp': m.timestamp.isoformat()
                }
                for m in self.metrics_history
            ]
            
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save metrics history: {e}")
    
    def analyze_evolution_request(self, question: str, context: str = "") -> EvolutionGuidanceResult:
        """
        Analyze whether an evolution should proceed and provide guidance.
        
        This is the main method that prevents repetitive loops and guides evolution decisions.
        """
        # Extract the proposed improvement type from the question
        proposed_feature = self._extract_feature_from_question(question)
        proposed_type = self._extract_type_from_question(question)
        
        # Check for repetitive patterns
        repetition_check = self._check_repetitive_pattern(proposed_feature, proposed_type)
        if not repetition_check['allowed']:
            return EvolutionGuidanceResult(
                should_evolve=False,
                recommended_area=None,
                reason=repetition_check['reason'],
                suggested_question=None,
                blocked_reason=repetition_check['reason'],
                alternative_suggestions=self._get_alternative_suggestions()
            )
        
        # Check evolution effectiveness
        effectiveness_check = self._check_evolution_effectiveness()
        if not effectiveness_check['allowed']:
            return EvolutionGuidanceResult(
                should_evolve=False,
                recommended_area=None,
                reason=effectiveness_check['reason'],
                suggested_question=None,
                blocked_reason=effectiveness_check['reason'],
                alternative_suggestions=self._get_alternative_suggestions()
            )
        
        # Check cooldown periods
        cooldown_check = self._check_cooldown_period()
        if not cooldown_check['allowed']:
            return EvolutionGuidanceResult(
                should_evolve=False,
                recommended_area=None,
                reason=cooldown_check['reason'],
                suggested_question=None,
                blocked_reason=cooldown_check['reason'],
                alternative_suggestions=[]
            )
        
        # If all checks pass, recommend proceeding or suggest alternatives
        recommendations = self.evolution_tracker.get_evolution_recommendations()
        
        if recommendations:
            # System has specific recommendations
            high_priority_recs = [r for r in recommendations if r['priority'] == 'high']
            if high_priority_recs:
                rec = high_priority_recs[0]
                return EvolutionGuidanceResult(
                    should_evolve=True,
                    recommended_area=rec['recommendation'],
                    reason=f"High priority recommendation: {rec['recommendation']}",
                    suggested_question=self._generate_question_for_recommendation(rec),
                    blocked_reason=None,
                    alternative_suggestions=[]
                )
        
        # Default: allow evolution but suggest diversification
        return EvolutionGuidanceResult(
            should_evolve=True,
            recommended_area=proposed_feature,
            reason="Evolution allowed with diversification suggestion",
            suggested_question=question,
            blocked_reason=None,
            alternative_suggestions=self._get_diversification_suggestions()
        )
    
    def _check_repetitive_pattern(self, proposed_feature: str, proposed_type: str) -> Dict:
        """Check if the proposed evolution is repetitive"""
        recent_evolutions = self.evolution_tracker.get_recent_evolutions(10)
        
        # Count same feature in recent evolutions
        same_feature_count = sum(
            1 for evo in recent_evolutions 
            if evo.get('feature', '') == proposed_feature
        )
        
        if same_feature_count >= self.repetition_threshold:
            return {
                'allowed': False,
                'reason': f"Repetitive pattern detected: '{proposed_feature}' attempted {same_feature_count} times recently. System may be stuck in a loop."
            }
        
        # Check for performance optimization specifically (the current crisis)
        if proposed_feature == 'performance_optimization':
            performance_count = sum(
                1 for evo in recent_evolutions 
                if 'performance' in evo.get('feature', '').lower()
            )
            
            if performance_count >= 5:
                return {
                    'allowed': False,
                    'reason': f"Performance optimization loop detected: {performance_count} performance-related evolutions recently. Need to diversify or validate effectiveness first."
                }
        
        return {'allowed': True, 'reason': 'No repetitive pattern detected'}
    
    def _check_evolution_effectiveness(self) -> Dict:
        """Check if recent evolutions have been effective"""
        if len(self.metrics_history) < 2:
            return {'allowed': True, 'reason': 'Insufficient metrics history for effectiveness check'}
        
        # Compare recent metrics to see if evolutions are helping
        recent_metrics = self.metrics_history[-3:]  # Last 3 measurements
        
        if len(recent_metrics) < 2:
            return {'allowed': True, 'reason': 'Insufficient recent metrics'}
        
        # Check if performance score is improving
        performance_trend = []
        for i in range(1, len(recent_metrics)):
            change = recent_metrics[i].performance_score - recent_metrics[i-1].performance_score
            performance_trend.append(change)
        
        avg_improvement = sum(performance_trend) / len(performance_trend)
        
        if avg_improvement < self.effectiveness_threshold:
            return {
                'allowed': False,
                'reason': f"Recent evolutions show minimal effectiveness (avg improvement: {avg_improvement:.2f}). Need to validate current improvements before adding more."
            }
        
        return {'allowed': True, 'reason': 'Recent evolutions show positive effectiveness'}
    
    def _check_cooldown_period(self) -> Dict:
        """Check if system is in cooldown period after failed evolution"""
        recent_evolutions = self.evolution_tracker.get_recent_evolutions(5)
        
        for evolution in recent_evolutions:
            if evolution.get('status') == 'rolled_back':
                rollback_time = datetime.fromisoformat(evolution.get('rollback_timestamp', evolution.get('timestamp')))
                time_since_rollback = datetime.now() - rollback_time
                
                if time_since_rollback < timedelta(hours=self.cooldown_hours):
                    hours_remaining = self.cooldown_hours - time_since_rollback.total_seconds() / 3600
                    return {
                        'allowed': False,
                        'reason': f"Cooldown period active after failed evolution. {hours_remaining:.1f} hours remaining before next evolution attempt."
                    }
        
        return {'allowed': True, 'reason': 'No active cooldown period'}
    
    def _extract_feature_from_question(self, question: str) -> str:
        """Extract feature type from evolution question"""
        question_lower = question.lower()
        
        # Use the same patterns as evolution tracker
        feature_patterns = {
            "performance": "performance_optimization",
            "testing": "testing_framework", 
            "security": "security_enhancement",
            "error": "error_handling",
            "monitoring": "monitoring_system",
            "caching": "caching_system",
            "api": "api_enhancement",
            "ui": "user_interface",
            "documentation": "documentation",
            "logging": "logging_system",
            "observability": "observability_system",
            "refactor": "code_refactoring",
            "validation": "validation_system",
            "configuration": "configuration_management",
            "rate limit": "rate_limiting",
            "debugging": "debugging_tools",
        }
        
        for pattern, feature in feature_patterns.items():
            if pattern in question_lower:
                return feature
        
        return "general_improvement"
    
    def _extract_type_from_question(self, question: str) -> str:
        """Extract evolution type from question"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["add", "implement", "create", "introduce"]):
            return "feature"
        elif any(word in question_lower for word in ["improve", "enhance", "optimize", "better"]):
            return "enhancement"
        elif any(word in question_lower for word in ["fix", "resolve", "correct", "bug"]):
            return "fix"
        elif any(word in question_lower for word in ["refactor", "reorganize", "restructure"]):
            return "refactor"
        
        return "enhancement"
    
    def _get_alternative_suggestions(self) -> List[str]:
        """Get alternative improvement suggestions to break repetitive patterns"""
        recommendations = self.evolution_tracker.get_evolution_recommendations()
        
        suggestions = []
        for rec in recommendations[:3]:  # Top 3 recommendations
            suggestions.append(rec['recommendation'])
        
        # Add general suggestions if no specific recommendations
        if not suggestions:
            suggestions = [
                "Focus on testing framework and code quality",
                "Implement security enhancements and vulnerability scanning", 
                "Add comprehensive error handling and resilience",
                "Improve user interface and user experience",
                "Enhance system documentation and onboarding"
            ]
        
        return suggestions
    
    def _get_diversification_suggestions(self) -> List[str]:
        """Get suggestions for evolution diversification"""
        summary = self.evolution_tracker.get_evolution_summary()
        evolution_types = summary.get('evolution_types', {})
        
        # Find underrepresented evolution types
        missing_types = []
        important_types = ['security', 'testing', 'fix', 'refactor', 'documentation']
        
        for etype in important_types:
            if evolution_types.get(etype, 0) == 0:
                missing_types.append(f"Consider adding {etype} evolutions")
        
        return missing_types[:3]  # Top 3 diversification suggestions
    
    def _generate_question_for_recommendation(self, recommendation: Dict) -> str:
        """Generate an evolution question based on a recommendation"""
        rec_type = recommendation.get('type', '')
        rec_text = recommendation.get('recommendation', '')
        
        if rec_type == 'missing_evolution_type':
            if 'security' in rec_text:
                return "What is the ONE most important security enhancement to implement to protect the debate system from vulnerabilities?"
            elif 'testing' in rec_text:
                return "What is the ONE most important testing improvement to implement to ensure system reliability and catch regressions?"
            elif 'fix' in rec_text:
                return "What is the ONE most critical bug or issue to fix in the current debate system?"
            elif 'refactor' in rec_text:
                return "What is the ONE most important code refactoring to improve maintainability and technical debt?"
        
        elif rec_type == 'low_diversity':
            return "What is the ONE most important improvement to make that's completely different from recent performance optimizations?"
        
        elif rec_type == 'imbalanced_evolution_types':
            return "What is the ONE most important non-performance improvement to balance the evolution portfolio?"
        
        return "What is the ONE most important improvement to make considering the current evolution patterns and system needs?"
    
    def record_evolution_metrics(self, current_metrics: EvolutionMetrics):
        """Record current system metrics for effectiveness tracking"""
        self.metrics_history.append(current_metrics)
        
        # Keep only recent metrics (last 50 measurements)
        if len(self.metrics_history) > 50:
            self.metrics_history = self.metrics_history[-50:]
        
        self._save_metrics_history()
    
    def get_system_health_report(self) -> Dict:
        """Generate a system health report for evolution guidance"""
        summary = self.evolution_tracker.get_evolution_summary()
        recommendations = self.evolution_tracker.get_evolution_recommendations()
        
        # Analyze recent pattern issues
        recent_evolutions = self.evolution_tracker.get_recent_evolutions(10)
        feature_counts = {}
        for evo in recent_evolutions:
            feature = evo.get('feature', 'unknown')
            feature_counts[feature] = feature_counts.get(feature, 0) + 1
        
        # Find the most repeated feature
        most_repeated = max(feature_counts.items(), key=lambda x: x[1]) if feature_counts else ("none", 0)
        
        # Calculate diversity score
        diversity_score = summary.get('diversity_score', 0.0)
        
        health_status = "healthy"
        if most_repeated[1] >= 3:
            health_status = "repetitive_pattern"
        elif diversity_score < 0.3:
            health_status = "low_diversity"
        elif len(recommendations) > 3:
            health_status = "needs_attention"
        
        return {
            "health_status": health_status,
            "diversity_score": diversity_score,
            "most_repeated_feature": most_repeated[0],
            "repetition_count": most_repeated[1],
            "total_evolutions": summary.get('total_evolutions', 0),
            "recommendations_count": len(recommendations),
            "high_priority_recommendations": len([r for r in recommendations if r['priority'] == 'high']),
            "metrics_history_count": len(self.metrics_history),
            "effectiveness_trend": self._calculate_effectiveness_trend()
        }
    
    def _calculate_effectiveness_trend(self) -> str:
        """Calculate the trend of evolution effectiveness"""
        if len(self.metrics_history) < 3:
            return "insufficient_data"
        
        recent_metrics = self.metrics_history[-3:]
        
        # Calculate average improvement over time
        improvements = []
        for i in range(1, len(recent_metrics)):
            perf_change = recent_metrics[i].performance_score - recent_metrics[i-1].performance_score
            stability_change = recent_metrics[i].system_stability - recent_metrics[i-1].system_stability
            avg_change = (perf_change + stability_change) / 2
            improvements.append(avg_change)
        
        avg_improvement = sum(improvements) / len(improvements)
        
        if avg_improvement > 0.1:
            return "improving"
        elif avg_improvement < -0.1:
            return "declining"
        else:
            return "stable"


# Example usage and testing
if __name__ == "__main__":
    # Test the evolution guidance system
    guidance = EvolutionGuidanceSystem()
    
    # Test a repetitive performance optimization question
    result = guidance.analyze_evolution_request(
        "What is the ONE most important performance optimization to make to this debate system?"
    )
    
    print("Evolution Guidance Result:")
    print(f"Should evolve: {result.should_evolve}")
    print(f"Reason: {result.reason}")
    if result.blocked_reason:
        print(f"Blocked: {result.blocked_reason}")
    if result.alternative_suggestions:
        print("Alternative suggestions:")
        for alt in result.alternative_suggestions:
            print(f"  - {alt}")
    
    # Test system health report
    print("\nSystem Health Report:")
    health = guidance.get_system_health_report()
    for key, value in health.items():
        print(f"  {key}: {value}")