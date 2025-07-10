"""
Orchestration Metrics and Logging

This module provides comprehensive metrics collection and logging for the orchestration system,
enabling monitoring, debugging, and performance analysis.
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class LogLevel(Enum):
    """Log levels for orchestration events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationEvent:
    """An orchestration event for logging."""
    event_id: str
    event_type: str
    debate_id: UUID
    session_id: Optional[UUID]
    timestamp: datetime
    level: LogLevel
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None
    rule_id: Optional[str] = None
    action_type: Optional[str] = None


@dataclass
class DebateMetrics:
    """Metrics for a single debate."""
    debate_id: UUID
    start_time: datetime
    end_time: Optional[datetime] = None
    total_rounds: int = 0
    total_arguments: int = 0
    participants: Set[str] = field(default_factory=set)
    rules_triggered: List[str] = field(default_factory=list)
    consensus_reached: bool = False
    consensus_confidence: float = 0.0
    escalated: bool = False
    completed_successfully: bool = False
    error_count: int = 0
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get debate duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def arguments_per_round(self) -> float:
        """Get average arguments per round."""
        return self.total_arguments / max(self.total_rounds, 1)


class MetricsCollector:
    """Collects and manages orchestration metrics."""
    
    def __init__(self, enable_file_export: bool = True, export_path: Optional[Path] = None):
        self.enable_file_export = enable_file_export
        self.export_path = export_path or Path("data/orchestration_metrics")
        self.export_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage
        self.metrics: List[MetricPoint] = []
        self.events: List[OrchestrationEvent] = []
        self.debate_metrics: Dict[UUID, DebateMetrics] = {}
        
        # Aggregated metrics
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = {}
        self.timers: Dict[str, List[float]] = {}
        
        # Configuration
        self.max_stored_metrics = 10000
        self.max_stored_events = 5000
        self.auto_export_interval = timedelta(minutes=5)
        self.last_export = datetime.now()
    
    def record_metric(
        self, 
        name: str, 
        value: float, 
        metric_type: MetricType,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a metric."""
        metric = MetricPoint(
            name=name,
            type=metric_type,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metadata=metadata or {}
        )
        
        self.metrics.append(metric)
        
        # Update aggregated metrics
        if metric_type == MetricType.COUNTER:
            self.counters[name] = self.counters.get(name, 0) + value
        elif metric_type == MetricType.GAUGE:
            self.gauges[name] = value
        elif metric_type == MetricType.HISTOGRAM:
            if name not in self.histograms:
                self.histograms[name] = []
            self.histograms[name].append(value)
        elif metric_type == MetricType.TIMER:
            if name not in self.timers:
                self.timers[name] = []
            self.timers[name].append(value)
        
        # Trim metrics if needed
        if len(self.metrics) > self.max_stored_metrics:
            self.metrics = self.metrics[-self.max_stored_metrics:]
        
        # Auto-export if needed
        if self.enable_file_export and datetime.now() - self.last_export > self.auto_export_interval:
            self.export_metrics()
    
    def log_event(
        self,
        event_type: str,
        debate_id: UUID,
        message: str,
        level: LogLevel = LogLevel.INFO,
        session_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        rule_id: Optional[str] = None,
        action_type: Optional[str] = None
    ):
        """Log an orchestration event."""
        event = OrchestrationEvent(
            event_id=f"{event_type}_{int(time.time() * 1000)}",
            event_type=event_type,
            debate_id=debate_id,
            session_id=session_id,
            timestamp=datetime.now(),
            level=level,
            message=message,
            context=context or {},
            duration_ms=duration_ms,
            rule_id=rule_id,
            action_type=action_type
        )
        
        self.events.append(event)
        
        # Log to standard logger as well
        log_func = getattr(logger, level.value)
        log_func(f"[{event_type}] {message}", extra={
            'debate_id': str(debate_id),
            'session_id': str(session_id) if session_id else None,
            'context': context
        })
        
        # Trim events if needed
        if len(self.events) > self.max_stored_events:
            self.events = self.events[-self.max_stored_events:]
    
    def start_debate_tracking(self, debate_id: UUID, participants: Set[str]):
        """Start tracking metrics for a debate."""
        self.debate_metrics[debate_id] = DebateMetrics(
            debate_id=debate_id,
            start_time=datetime.now(),
            participants=participants
        )
        
        self.record_metric("debates_started", 1, MetricType.COUNTER)
        self.log_event("debate_started", debate_id, f"Started tracking debate with {len(participants)} participants")
    
    def end_debate_tracking(
        self, 
        debate_id: UUID, 
        completed_successfully: bool = True,
        consensus_reached: bool = False,
        consensus_confidence: float = 0.0
    ):
        """End tracking metrics for a debate."""
        if debate_id not in self.debate_metrics:
            logger.warning(f"No metrics found for debate {debate_id}")
            return
        
        debate_metrics = self.debate_metrics[debate_id]
        debate_metrics.end_time = datetime.now()
        debate_metrics.completed_successfully = completed_successfully
        debate_metrics.consensus_reached = consensus_reached
        debate_metrics.consensus_confidence = consensus_confidence
        
        # Record final metrics
        if debate_metrics.duration:
            self.record_metric("debate_duration_seconds", debate_metrics.duration.total_seconds(), MetricType.TIMER)
        
        self.record_metric("debate_rounds", debate_metrics.total_rounds, MetricType.HISTOGRAM)
        self.record_metric("debate_arguments", debate_metrics.total_arguments, MetricType.HISTOGRAM)
        self.record_metric("arguments_per_round", debate_metrics.arguments_per_round, MetricType.HISTOGRAM)
        
        if completed_successfully:
            self.record_metric("debates_completed", 1, MetricType.COUNTER)
        else:
            self.record_metric("debates_failed", 1, MetricType.COUNTER)
        
        if consensus_reached:
            self.record_metric("debates_with_consensus", 1, MetricType.COUNTER)
            self.record_metric("consensus_confidence", consensus_confidence, MetricType.HISTOGRAM)
        
        self.log_event(
            "debate_completed", 
            debate_id, 
            f"Debate completed: {debate_metrics.total_rounds} rounds, {debate_metrics.total_arguments} arguments",
            context={
                'duration_seconds': debate_metrics.duration.total_seconds() if debate_metrics.duration else None,
                'consensus_reached': consensus_reached,
                'consensus_confidence': consensus_confidence
            }
        )
    
    def record_rule_triggered(self, rule_id: str, debate_id: UUID, action_count: int):
        """Record that a rule was triggered."""
        self.record_metric("rules_triggered", 1, MetricType.COUNTER, tags={"rule_id": rule_id})
        self.record_metric("rule_actions", action_count, MetricType.HISTOGRAM, tags={"rule_id": rule_id})
        
        if debate_id in self.debate_metrics:
            self.debate_metrics[debate_id].rules_triggered.append(rule_id)
        
        self.log_event(
            "rule_triggered",
            debate_id,
            f"Rule {rule_id} triggered with {action_count} actions",
            rule_id=rule_id
        )
    
    def record_action_executed(self, action_type: str, debate_id: UUID, duration_ms: float, success: bool):
        """Record action execution."""
        self.record_metric("actions_executed", 1, MetricType.COUNTER, tags={"action_type": action_type})
        self.record_metric("action_duration_ms", duration_ms, MetricType.TIMER, tags={"action_type": action_type})
        
        if success:
            self.record_metric("actions_successful", 1, MetricType.COUNTER, tags={"action_type": action_type})
        else:
            self.record_metric("actions_failed", 1, MetricType.COUNTER, tags={"action_type": action_type})
            if debate_id in self.debate_metrics:
                self.debate_metrics[debate_id].error_count += 1
        
        self.log_event(
            "action_executed",
            debate_id,
            f"Action {action_type} {'succeeded' if success else 'failed'} in {duration_ms:.2f}ms",
            duration_ms=duration_ms,
            action_type=action_type,
            level=LogLevel.INFO if success else LogLevel.ERROR
        )
    
    def record_round_completed(self, debate_id: UUID, round_number: int, argument_count: int):
        """Record round completion."""
        if debate_id in self.debate_metrics:
            metrics = self.debate_metrics[debate_id]
            metrics.total_rounds = round_number
            metrics.total_arguments += argument_count
        
        self.record_metric("rounds_completed", 1, MetricType.COUNTER)
        self.record_metric("round_arguments", argument_count, MetricType.HISTOGRAM)
        
        self.log_event(
            "round_completed",
            debate_id,
            f"Round {round_number} completed with {argument_count} arguments"
        )
    
    def record_escalation(self, debate_id: UUID, reason: str):
        """Record debate escalation."""
        if debate_id in self.debate_metrics:
            self.debate_metrics[debate_id].escalated = True
        
        self.record_metric("debates_escalated", 1, MetricType.COUNTER)
        
        self.log_event(
            "debate_escalated",
            debate_id,
            f"Debate escalated: {reason}",
            level=LogLevel.WARNING,
            context={"escalation_reason": reason}
        )
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        active_debates = sum(1 for m in self.debate_metrics.values() if m.end_time is None)
        completed_debates = sum(1 for m in self.debate_metrics.values() if m.end_time is not None)
        
        # Calculate averages
        completed_metrics = [m for m in self.debate_metrics.values() if m.end_time is not None]
        avg_duration = 0.0
        avg_rounds = 0.0
        avg_arguments = 0.0
        consensus_rate = 0.0
        
        if completed_metrics:
            durations = [m.duration.total_seconds() for m in completed_metrics if m.duration]
            avg_duration = sum(durations) / len(durations) if durations else 0.0
            
            total_completed = len(completed_metrics)
            avg_rounds = sum(m.total_rounds for m in completed_metrics) / total_completed if total_completed > 0 else 0.0
            avg_arguments = sum(m.total_arguments for m in completed_metrics) / total_completed if total_completed > 0 else 0.0
            consensus_rate = sum(1 for m in completed_metrics if m.consensus_reached) / total_completed if total_completed > 0 else 0.0
        
        return {
            'debates': {
                'active': active_debates,
                'completed': completed_debates,
                'total': len(self.debate_metrics)
            },
            'averages': {
                'duration_seconds': avg_duration,
                'rounds_per_debate': avg_rounds,
                'arguments_per_debate': avg_arguments,
                'consensus_rate': consensus_rate
            },
            'counters': self.counters.copy(),
            'gauges': self.gauges.copy(),
            'system': {
                'metrics_collected': len(self.metrics),
                'events_logged': len(self.events),
                'last_export': self.last_export.isoformat()
            }
        }
    
    def get_debate_metrics(self, debate_id: UUID) -> Optional[DebateMetrics]:
        """Get metrics for a specific debate."""
        return self.debate_metrics.get(debate_id)
    
    def get_rule_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for rules."""
        rule_stats = {}
        
        # Count rule triggers
        for event in self.events:
            if event.event_type == "rule_triggered" and event.rule_id:
                if event.rule_id not in rule_stats:
                    rule_stats[event.rule_id] = {
                        'trigger_count': 0,
                        'total_duration_ms': 0.0,
                        'avg_duration_ms': 0.0,
                        'last_triggered': None
                    }
                
                rule_stats[event.rule_id]['trigger_count'] += 1
                rule_stats[event.rule_id]['last_triggered'] = event.timestamp
                
                if event.duration_ms:
                    rule_stats[event.rule_id]['total_duration_ms'] += event.duration_ms
        
        # Calculate averages
        for rule_id, stats in rule_stats.items():
            if stats['trigger_count'] > 0:
                stats['avg_duration_ms'] = stats['total_duration_ms'] / stats['trigger_count']
        
        return rule_stats
    
    def export_metrics(self):
        """Export metrics to file."""
        if not self.enable_file_export:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Export summary stats
            summary_file = self.export_path / f"summary_{timestamp}.json"
            with open(summary_file, 'w') as f:
                json.dump(self.get_summary_stats(), f, indent=2, default=str)
            
            # Export recent events
            recent_events = [asdict(event) for event in self.events[-100:]]
            events_file = self.export_path / f"events_{timestamp}.json"
            with open(events_file, 'w') as f:
                json.dump(recent_events, f, indent=2, default=str)
            
            # Export debate metrics
            debate_data = {}
            for debate_id, metrics in self.debate_metrics.items():
                try:
                    debate_data[str(debate_id)] = asdict(metrics)
                except Exception as e:
                    logger.warning(f"Failed to serialize metrics for debate {debate_id}: {e}")
            
            debates_file = self.export_path / f"debates_{timestamp}.json"
            with open(debates_file, 'w') as f:
                json.dump(debate_data, f, indent=2, default=str)
            
            self.last_export = datetime.now()
            logger.info(f"Exported metrics to {self.export_path}")
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
    
    def clear_old_data(self, days_to_keep: int = 7):
        """Clear old metrics data."""
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        
        # Clear old metrics
        self.metrics = [m for m in self.metrics if m.timestamp > cutoff]
        
        # Clear old events
        self.events = [e for e in self.events if e.timestamp > cutoff]
        
        # Clear old debate metrics
        old_debates = [
            debate_id for debate_id, metrics in self.debate_metrics.items()
            if metrics.end_time and metrics.end_time < cutoff
        ]
        
        for debate_id in old_debates:
            del self.debate_metrics[debate_id]
        
        logger.info(f"Cleared metrics older than {days_to_keep} days")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def initialize_metrics(enable_file_export: bool = True, export_path: Optional[Path] = None):
    """Initialize the global metrics collector."""
    global _metrics_collector
    _metrics_collector = MetricsCollector(enable_file_export, export_path)
    return _metrics_collector


# Convenience functions
def record_metric(name: str, value: float, metric_type: MetricType, **kwargs):
    """Record a metric using the global collector."""
    get_metrics_collector().record_metric(name, value, metric_type, **kwargs)


def log_orchestration_event(event_type: str, debate_id: UUID, message: str, **kwargs):
    """Log an orchestration event using the global collector."""
    get_metrics_collector().log_event(event_type, debate_id, message, **kwargs)