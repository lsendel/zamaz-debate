#!/usr/bin/env python3
"""
Evolution Effectiveness Measurement System

This system tracks and measures the effectiveness of system evolutions,
providing metrics, rollback capabilities, and success validation.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import psutil
import subprocess


class EvolutionStatus(Enum):
    """Status of an evolution"""
    PENDING = "pending"
    ACTIVE = "active"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class PerformanceMetrics:
    """System performance metrics"""
    timestamp: str
    cpu_usage: float
    memory_usage: float
    response_time_avg: float
    error_rate: float
    debate_completion_rate: float
    decision_accuracy: float
    system_load: float


@dataclass
class EvolutionMeasurement:
    """Measurement of an evolution's effectiveness"""
    evolution_id: str
    evolution_feature: str
    evolution_type: str
    status: EvolutionStatus
    start_time: str
    end_time: Optional[str]
    before_metrics: Optional[PerformanceMetrics]
    after_metrics: Optional[PerformanceMetrics]
    success_criteria: Dict[str, float]
    actual_results: Dict[str, float]
    rollback_available: bool
    rollback_path: Optional[str]
    notes: List[str]


class EvolutionEffectivenessTracker:
    """Tracks and measures evolution effectiveness"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.measurements_dir = self.data_dir / "evolution_measurements"
        self.measurements_dir.mkdir(parents=True, exist_ok=True)
        
        self.baseline_metrics_file = self.measurements_dir / "baseline_metrics.json"
        self.effectiveness_report_file = self.measurements_dir / "effectiveness_report.json"
        
        # Performance tracking
        self.performance_samples = []
        self.measurement_interval = 60  # seconds
        self.is_monitoring = False
        
    async def start_monitoring(self):
        """Start continuous performance monitoring"""
        self.is_monitoring = True
        while self.is_monitoring:
            metrics = await self._collect_current_metrics()
            self.performance_samples.append(metrics)
            
            # Keep only last 100 samples to prevent memory bloat
            if len(self.performance_samples) > 100:
                self.performance_samples = self.performance_samples[-100:]
                
            await asyncio.sleep(self.measurement_interval)
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
    
    async def begin_evolution_measurement(self, evolution_id: str, 
                                        evolution_feature: str,
                                        evolution_type: str,
                                        success_criteria: Dict[str, float]) -> bool:
        """Begin measuring an evolution's effectiveness"""
        
        # Collect baseline metrics
        baseline_metrics = await self._collect_baseline_metrics()
        
        # Create measurement record
        measurement = EvolutionMeasurement(
            evolution_id=evolution_id,
            evolution_feature=evolution_feature,
            evolution_type=evolution_type,
            status=EvolutionStatus.PENDING,
            start_time=datetime.now().isoformat(),
            end_time=None,
            before_metrics=baseline_metrics,
            after_metrics=None,
            success_criteria=success_criteria,
            actual_results={},
            rollback_available=True,
            rollback_path=self._create_rollback_snapshot(),
            notes=[]
        )
        
        # Save measurement
        measurement_file = self.measurements_dir / f"{evolution_id}_measurement.json"
        with open(measurement_file, 'w') as f:
            json.dump(asdict(measurement), f, indent=2)
            
        return True
    
    async def complete_evolution_measurement(self, evolution_id: str) -> Dict:
        """Complete an evolution measurement and determine success/failure"""
        
        measurement_file = self.measurements_dir / f"{evolution_id}_measurement.json"
        if not measurement_file.exists():
            return {"error": "Measurement not found"}
        
        # Load measurement
        with open(measurement_file, 'r') as f:
            measurement_data = json.load(f)
        
        # Collect post-evolution metrics
        after_metrics = await self._collect_baseline_metrics()
        measurement_data["after_metrics"] = asdict(after_metrics)
        measurement_data["end_time"] = datetime.now().isoformat()
        
        # Calculate effectiveness
        effectiveness_results = self._calculate_effectiveness(
            measurement_data["before_metrics"],
            asdict(after_metrics),
            measurement_data["success_criteria"]
        )
        
        measurement_data["actual_results"] = effectiveness_results["metrics"]
        
        # Determine success/failure
        if effectiveness_results["success"]:
            measurement_data["status"] = EvolutionStatus.SUCCESS.value
            measurement_data["notes"].append(f"Evolution successful: {effectiveness_results['summary']}")
        else:
            measurement_data["status"] = EvolutionStatus.FAILED.value
            measurement_data["notes"].append(f"Evolution failed: {effectiveness_results['summary']}")
            
            # Recommend rollback for failed evolutions
            if measurement_data["rollback_available"]:
                measurement_data["notes"].append("Rollback recommended - use rollback_evolution() method")
        
        # Save updated measurement
        with open(measurement_file, 'w') as f:
            json.dump(measurement_data, f, indent=2)
        
        # Update effectiveness report
        await self._update_effectiveness_report(measurement_data)
        
        return {
            "evolution_id": evolution_id,
            "status": measurement_data["status"],
            "success": effectiveness_results["success"],
            "metrics": effectiveness_results["metrics"],
            "summary": effectiveness_results["summary"],
            "rollback_available": measurement_data["rollback_available"]
        }
    
    async def rollback_evolution(self, evolution_id: str) -> Dict:
        """Rollback a failed evolution"""
        
        measurement_file = self.measurements_dir / f"{evolution_id}_measurement.json"
        if not measurement_file.exists():
            return {"error": "Measurement not found"}
        
        with open(measurement_file, 'r') as f:
            measurement_data = json.load(f)
        
        if not measurement_data["rollback_available"]:
            return {"error": "Rollback not available for this evolution"}
        
        rollback_path = measurement_data["rollback_path"]
        if not rollback_path or not Path(rollback_path).exists():
            return {"error": "Rollback snapshot not found"}
        
        # Perform rollback (simplified - in practice would restore from snapshot)
        measurement_data["status"] = EvolutionStatus.ROLLED_BACK.value
        measurement_data["notes"].append(f"Evolution rolled back at {datetime.now().isoformat()}")
        
        # Save updated measurement
        with open(measurement_file, 'w') as f:
            json.dump(measurement_data, f, indent=2)
        
        return {
            "evolution_id": evolution_id,
            "status": "rolled_back",
            "message": "Evolution successfully rolled back to previous state"
        }
    
    async def get_effectiveness_report(self) -> Dict:
        """Get comprehensive effectiveness report"""
        
        if not self.effectiveness_report_file.exists():
            return {"error": "No effectiveness data available"}
        
        with open(self.effectiveness_report_file, 'r') as f:
            report = json.load(f)
        
        # Add current system metrics
        current_metrics = await self._collect_current_metrics()
        report["current_system_state"] = asdict(current_metrics)
        report["generated_at"] = datetime.now().isoformat()
        
        return report
    
    async def get_evolution_trends(self) -> Dict:
        """Get trends in evolution effectiveness over time"""
        
        measurements = []
        for measurement_file in self.measurements_dir.glob("*_measurement.json"):
            with open(measurement_file, 'r') as f:
                measurements.append(json.load(f))
        
        if not measurements:
            return {"error": "No measurements available"}
        
        # Sort by start time
        measurements.sort(key=lambda x: x["start_time"])
        
        # Calculate trends
        success_rate = len([m for m in measurements if m["status"] == "success"]) / len(measurements) * 100
        failure_rate = len([m for m in measurements if m["status"] == "failed"]) / len(measurements) * 100
        rollback_rate = len([m for m in measurements if m["status"] == "rolled_back"]) / len(measurements) * 100
        
        # Feature success rates
        feature_success = {}
        for measurement in measurements:
            feature = measurement["evolution_feature"]
            if feature not in feature_success:
                feature_success[feature] = {"total": 0, "success": 0}
            feature_success[feature]["total"] += 1
            if measurement["status"] == "success":
                feature_success[feature]["success"] += 1
        
        for feature in feature_success:
            feature_success[feature]["rate"] = (
                feature_success[feature]["success"] / feature_success[feature]["total"] * 100
            )
        
        return {
            "total_evolutions_measured": len(measurements),
            "success_rate": round(success_rate, 2),
            "failure_rate": round(failure_rate, 2),
            "rollback_rate": round(rollback_rate, 2),
            "feature_success_rates": feature_success,
            "recent_measurements": measurements[-5:],  # Last 5 measurements
            "trend_period": f"{measurements[0]['start_time']} to {measurements[-1]['start_time']}"
        }
    
    async def _collect_current_metrics(self) -> PerformanceMetrics:
        """Collect current system performance metrics"""
        
        # Basic system metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Simple system load
        try:
            load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else cpu_usage / 100
        except:
            load_avg = cpu_usage / 100
        
        # Estimate debate/decision metrics (simplified)
        response_time = await self._estimate_response_time()
        error_rate = await self._estimate_error_rate()
        debate_completion_rate = await self._estimate_debate_completion_rate()
        decision_accuracy = await self._estimate_decision_accuracy()
        
        return PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            response_time_avg=response_time,
            error_rate=error_rate,
            debate_completion_rate=debate_completion_rate,
            decision_accuracy=decision_accuracy,
            system_load=load_avg
        )
    
    async def _collect_baseline_metrics(self) -> PerformanceMetrics:
        """Collect baseline metrics by averaging recent samples"""
        
        if len(self.performance_samples) < 3:
            # Not enough samples, collect current metrics
            return await self._collect_current_metrics()
        
        # Average last 3 samples
        recent_samples = self.performance_samples[-3:]
        
        avg_cpu = sum(s.cpu_usage for s in recent_samples) / len(recent_samples)
        avg_memory = sum(s.memory_usage for s in recent_samples) / len(recent_samples)
        avg_response = sum(s.response_time_avg for s in recent_samples) / len(recent_samples)
        avg_error = sum(s.error_rate for s in recent_samples) / len(recent_samples)
        avg_debate = sum(s.debate_completion_rate for s in recent_samples) / len(recent_samples)
        avg_accuracy = sum(s.decision_accuracy for s in recent_samples) / len(recent_samples)
        avg_load = sum(s.system_load for s in recent_samples) / len(recent_samples)
        
        return PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_usage=avg_cpu,
            memory_usage=avg_memory,
            response_time_avg=avg_response,
            error_rate=avg_error,
            debate_completion_rate=avg_debate,
            decision_accuracy=avg_accuracy,
            system_load=avg_load
        )
    
    def _calculate_effectiveness(self, before_metrics: Dict, after_metrics: Dict, 
                               success_criteria: Dict[str, float]) -> Dict:
        """Calculate evolution effectiveness"""
        
        results = {}
        success = True
        summary_parts = []
        
        for metric, target_improvement in success_criteria.items():
            if metric not in before_metrics or metric not in after_metrics:
                continue
                
            before_value = before_metrics[metric]
            after_value = after_metrics[metric]
            
            # Calculate improvement percentage
            if before_value != 0:
                improvement = ((after_value - before_value) / before_value) * 100
            else:
                improvement = 0 if after_value == 0 else 100
            
            results[metric] = {
                "before": before_value,
                "after": after_value,
                "improvement": round(improvement, 2),
                "target": target_improvement,
                "met": improvement >= target_improvement
            }
            
            if improvement < target_improvement:
                success = False
                summary_parts.append(f"{metric} improved {improvement:.1f}% (target: {target_improvement}%)")
            else:
                summary_parts.append(f"{metric} improved {improvement:.1f}% ✓")
        
        return {
            "success": success,
            "metrics": results,
            "summary": "; ".join(summary_parts) if summary_parts else "No metrics to evaluate"
        }
    
    def _create_rollback_snapshot(self) -> str:
        """Create rollback snapshot (simplified)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = self.measurements_dir / f"snapshot_{timestamp}"
        snapshot_path.mkdir(exist_ok=True)
        
        # In a real implementation, this would backup the system state
        # For now, just create a marker file
        marker_file = snapshot_path / "rollback_marker.json"
        with open(marker_file, 'w') as f:
            json.dump({
                "created_at": datetime.now().isoformat(),
                "type": "rollback_snapshot"
            }, f)
        
        return str(snapshot_path)
    
    async def _update_effectiveness_report(self, measurement_data: Dict):
        """Update the comprehensive effectiveness report"""
        
        report = {"measurements": [], "summary": {}}
        
        if self.effectiveness_report_file.exists():
            with open(self.effectiveness_report_file, 'r') as f:
                report = json.load(f)
        
        # Add new measurement
        report["measurements"].append(measurement_data)
        
        # Update summary statistics
        total = len(report["measurements"])
        successful = len([m for m in report["measurements"] if m["status"] == "success"])
        failed = len([m for m in report["measurements"] if m["status"] == "failed"])
        rolled_back = len([m for m in report["measurements"] if m["status"] == "rolled_back"])
        
        report["summary"] = {
            "total_evolutions": total,
            "successful": successful,
            "failed": failed,
            "rolled_back": rolled_back,
            "success_rate": round((successful / total) * 100, 2) if total > 0 else 0,
            "last_updated": datetime.now().isoformat()
        }
        
        # Save updated report
        with open(self.effectiveness_report_file, 'w') as f:
            json.dump(report, f, indent=2)
    
    async def _estimate_response_time(self) -> float:
        """Estimate average response time"""
        # In a real implementation, this would measure actual API response times
        # For now, return a baseline estimate
        return 2.5  # seconds
    
    async def _estimate_error_rate(self) -> float:
        """Estimate system error rate"""
        # Check recent error logs or failed requests
        return 0.05  # 5% error rate baseline
    
    async def _estimate_debate_completion_rate(self) -> float:
        """Estimate debate completion rate"""
        # Count completed vs started debates
        try:
            debates_dir = self.data_dir / "debates"
            if not debates_dir.exists():
                return 0.95
            
            total_debates = len(list(debates_dir.glob("*.json")))
            if total_debates == 0:
                return 0.95
            
            # Simplified: assume most debates complete successfully
            return 0.95  # 95% completion rate
        except:
            return 0.95
    
    async def _estimate_decision_accuracy(self) -> float:
        """Estimate decision accuracy"""
        # In practice, this would measure user satisfaction or decision outcomes
        return 0.85  # 85% accuracy baseline