#!/usr/bin/env python3
"""
Enhanced Evolution Tracker with Effectiveness Framework Integration

This enhanced version integrates the Evolution Effectiveness Framework to provide
better tracking, validation, and rollback capabilities for system evolutions.
"""

import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.contexts.evolution_effectiveness import (
    EvolutionEffectivenessService,
    MetricsCollectionService,
    JsonEvolutionEffectivenessRepository,
    JsonMetricsRepository,
    EvolutionEffectivenessQueryService,
    SuccessMetric,
    MetricType
)
from .evolution_tracker import EvolutionTracker  # Import the original for compatibility


class EnhancedEvolutionTracker(EvolutionTracker):
    """
    Enhanced evolution tracker with effectiveness validation and rollback capabilities
    """
    
    def __init__(self, evolutions_dir: str = None, enable_effectiveness_framework: bool = True):
        # Initialize the base tracker
        super().__init__(evolutions_dir)
        
        # Initialize effectiveness framework
        self.enable_effectiveness_framework = enable_effectiveness_framework
        
        if enable_effectiveness_framework:
            self.effectiveness_service = EvolutionEffectivenessService()
            self.metrics_service = MetricsCollectionService()
            self.effectiveness_repo = JsonEvolutionEffectivenessRepository()
            self.metrics_repo = JsonMetricsRepository()
            self.query_service = EvolutionEffectivenessQueryService(
                self.effectiveness_repo,
                self.metrics_repo,
                None  # Reports repo not needed for basic functionality
            )
    
    async def add_evolution_with_validation(self, evolution: Dict) -> Dict:
        """
        Add evolution with full effectiveness validation and assessment
        
        Returns:
            Dict with evolution result and effectiveness assessment
        """
        # First check for duplicates using the original logic
        if self.is_duplicate(evolution):
            return {
                "success": False,
                "reason": "duplicate_detected",
                "evolution_id": None,
                "effectiveness_assessment": None
            }
        
        # Validate evolution structure
        if not self._validate_evolution(evolution):
            return {
                "success": False,
                "reason": "validation_failed",
                "evolution_id": None,
                "effectiveness_assessment": None
            }
        
        # Check system health before adding evolution
        if self.enable_effectiveness_framework:
            system_health = await self._check_system_health()
            if not system_health["should_proceed"]:
                return {
                    "success": False,
                    "reason": "system_health_check_failed",
                    "evolution_id": None,
                    "effectiveness_assessment": None,
                    "health_issues": system_health["issues"]
                }
        
        # Add evolution using original logic
        evolution_added = self.add_evolution(evolution)
        
        if not evolution_added:
            return {
                "success": False,
                "reason": "add_evolution_failed",
                "evolution_id": None,
                "effectiveness_assessment": None
            }
        
        evolution_id = evolution.get("id", f"evolution_{len(self.history['evolutions'])}")
        
        # If effectiveness framework is enabled, assess the evolution
        effectiveness_assessment = None
        if self.enable_effectiveness_framework:
            try:
                effectiveness_assessment = await self._assess_evolution_effectiveness(evolution_id, evolution)
            except Exception as e:
                print(f"Warning: Evolution effectiveness assessment failed: {e}")
        
        return {
            "success": True,
            "reason": "evolution_added_successfully",
            "evolution_id": evolution_id,
            "effectiveness_assessment": effectiveness_assessment
        }
    
    async def _check_system_health(self) -> Dict:
        """Check system health before allowing new evolutions"""
        try:
            # Load evolution history
            evolution_history = self.history.get("evolutions", [])
            
            # Assess system health
            health = await self.effectiveness_service.assess_evolution_health(evolution_history)
            
            issues = []
            should_proceed = True
            
            # Check for concerning patterns
            if health.concerning_patterns:
                high_risk_patterns = [p for p in health.concerning_patterns if p.risk_level == "high"]
                if high_risk_patterns:
                    issues.append("High-risk evolution patterns detected")
                    should_proceed = False
            
            # Check repetition risk
            if health.repetition_risk > 0.7:
                issues.append("High repetition risk detected")
                should_proceed = False
            
            # Check technical debt
            if health.technical_debt_level == "high":
                issues.append("High technical debt level")
                # Don't block for technical debt, but warn
            
            # Check if system is healthy
            if not health.is_healthy():
                issues.append("Overall system health is poor")
                # Don't block if it's just moderate issues
                if health.get_health_score() < 30:
                    should_proceed = False
            
            return {
                "should_proceed": should_proceed,
                "issues": issues,
                "health_score": health.get_health_score(),
                "repetition_risk": health.repetition_risk,
                "technical_debt_level": health.technical_debt_level
            }
            
        except Exception as e:
            print(f"Health check failed: {e}")
            # If health check fails, allow evolution but warn
            return {
                "should_proceed": True,
                "issues": [f"Health check failed: {str(e)}"],
                "health_score": 0.0,
                "repetition_risk": 0.0,
                "technical_debt_level": "unknown"
            }
    
    async def _assess_evolution_effectiveness(self, evolution_id: str, evolution: Dict) -> Dict:
        """Assess the effectiveness of a newly added evolution"""
        try:
            # Create effectiveness assessment
            evolution_effectiveness = await self.effectiveness_service.assess_evolution_effectiveness(evolution_id)
            
            # Store the assessment
            await self.effectiveness_repo.save(evolution_effectiveness)
            
            # Get the assessment results
            latest_score = evolution_effectiveness.effectiveness_scores[-1] if evolution_effectiveness.effectiveness_scores else None
            latest_validation = evolution_effectiveness.validation_results[-1] if evolution_effectiveness.validation_results else None
            
            assessment_result = {
                "assessment_id": str(evolution_effectiveness.id),
                "evolution_id": evolution_id,
                "effectiveness_score": latest_score.overall_score if latest_score else 0.0,
                "effectiveness_level": latest_score.effectiveness_level.value if latest_score else "unknown",
                "validation_status": evolution_effectiveness.status.value,
                "issues_found": latest_validation.issues_found if latest_validation else [],
                "recommendations": latest_validation.recommendations if latest_validation else [],
                "should_rollback": latest_validation.should_rollback if latest_validation else False,
                "assessed_at": datetime.now().isoformat()
            }
            
            # Check if rollback is recommended
            if assessment_result["should_rollback"]:
                await self._handle_evolution_rollback(evolution_id, evolution, assessment_result)
            
            return assessment_result
            
        except Exception as e:
            print(f"Evolution effectiveness assessment failed: {e}")
            return {
                "assessment_id": None,
                "evolution_id": evolution_id,
                "effectiveness_score": 0.0,
                "effectiveness_level": "unknown",
                "validation_status": "failed",
                "issues_found": [f"Assessment failed: {str(e)}"],
                "recommendations": ["Manual review recommended"],
                "should_rollback": False,
                "assessed_at": datetime.now().isoformat()
            }
    
    async def _handle_evolution_rollback(self, evolution_id: str, evolution: Dict, assessment_result: Dict):
        """Handle automatic rollback of ineffective evolution"""
        try:
            # Mark evolution as rolled back in the tracker
            for evo in self.history["evolutions"]:
                if evo.get("id") == evolution_id:
                    evo["status"] = "rolled_back"
                    evo["rollback_timestamp"] = datetime.now().isoformat()
                    evo["rollback_reason"] = "Automatic rollback due to effectiveness assessment"
                    break
            
            # Save updated history
            self._save_history()
            
            print(f"Evolution {evolution_id} has been automatically rolled back due to effectiveness concerns")
            
        except Exception as e:
            print(f"Evolution rollback failed: {e}")
    
    async def get_evolution_effectiveness_summary(self) -> Dict:
        """Get summary of evolution effectiveness"""
        if not self.enable_effectiveness_framework:
            return {"framework_enabled": False}
        
        try:
            summary = await self.query_service.get_effectiveness_summary()
            
            # Add system health information
            evolution_history = self.history.get("evolutions", [])
            health = await self.effectiveness_service.assess_evolution_health(evolution_history)
            
            summary.update({
                "framework_enabled": True,
                "system_health": {
                    "health_score": health.get_health_score(),
                    "is_healthy": health.is_healthy(),
                    "effectiveness_trend": health.effectiveness_trend,
                    "repetition_risk": health.repetition_risk,
                    "technical_debt_level": health.technical_debt_level,
                    "diversity_score": health.diversity_score
                },
                "concerning_patterns_count": len(health.concerning_patterns)
            })
            
            return summary
            
        except Exception as e:
            print(f"Failed to get effectiveness summary: {e}")
            return {
                "framework_enabled": True,
                "error": str(e)
            }
    
    async def get_problematic_evolutions(self) -> List[Dict]:
        """Get list of evolutions with effectiveness problems"""
        if not self.enable_effectiveness_framework:
            return []
        
        try:
            return await self.query_service.find_problematic_evolutions()
        except Exception as e:
            print(f"Failed to get problematic evolutions: {e}")
            return []
    
    def should_evolve_enhanced(self) -> Dict:
        """Enhanced version of should_evolve with effectiveness framework insights"""
        # Get basic throttling result
        basic_result = self.should_evolve()
        
        if not basic_result:
            return {
                "should_evolve": False,
                "reason": "basic_throttling_rules",
                "framework_enabled": self.enable_effectiveness_framework
            }
        
        if not self.enable_effectiveness_framework:
            return {
                "should_evolve": True,
                "reason": "basic_throttling_passed",
                "framework_enabled": False
            }
        
        # Add effectiveness framework checks
        try:
            # Run synchronous version of health check
            # (This is a simplified version - in production you'd want to cache health data)
            recent_evolutions = self.get_recent_evolutions(5)
            
            # Check for repetitive patterns
            if len(recent_evolutions) >= 3:
                recent_features = [evo.get("feature", "") for evo in recent_evolutions]
                unique_features = set(recent_features)
                
                if len(unique_features) == 1:
                    return {
                        "should_evolve": False,
                        "reason": "repetitive_pattern_detected",
                        "framework_enabled": True,
                        "details": f"Last {len(recent_evolutions)} evolutions all have feature: {recent_features[0]}"
                    }
            
            return {
                "should_evolve": True,
                "reason": "all_checks_passed",
                "framework_enabled": True
            }
            
        except Exception as e:
            print(f"Enhanced evolution check failed: {e}")
            return {
                "should_evolve": True,
                "reason": "enhanced_check_failed_fallback_to_basic",
                "framework_enabled": True,
                "error": str(e)
            }
    
    def get_evolution_recommendations(self) -> List[Dict]:
        """Get enhanced recommendations for improving evolution effectiveness"""
        base_recommendations = super().get_evolution_recommendations()
        
        if not self.enable_effectiveness_framework:
            return base_recommendations
        
        # Add effectiveness framework recommendations
        enhanced_recommendations = base_recommendations.copy()
        
        # Check recent evolution patterns
        recent_evolutions = self.get_recent_evolutions(10)
        
        if recent_evolutions:
            # Check for performance optimization overload
            performance_count = sum(1 for evo in recent_evolutions 
                                  if "performance" in evo.get("feature", "").lower())
            
            if performance_count >= 3:
                enhanced_recommendations.append({
                    "type": "repetitive_performance_optimization",
                    "recommendation": "Stop performance optimizations until effectiveness is validated",
                    "priority": "high",
                    "details": f"Found {performance_count} performance-related evolutions in recent history"
                })
            
            # Check for lack of validation/testing evolutions
            validation_count = sum(1 for evo in recent_evolutions 
                                 if any(keyword in evo.get("feature", "").lower() 
                                       for keyword in ["test", "validation", "quality"]))
            
            if validation_count == 0 and len(recent_evolutions) >= 5:
                enhanced_recommendations.append({
                    "type": "missing_validation_focus",
                    "recommendation": "Add testing and validation evolutions to improve code quality",
                    "priority": "medium",
                    "details": "No testing or validation evolutions found in recent history"
                })
        
        return enhanced_recommendations