"""
Analytics Dashboard for Orchestration System

This module provides analytics and monitoring capabilities for detecting edge cases,
analyzing patterns, and providing insights into debate orchestration performance.
"""

import json
import logging
import statistics
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from src.orchestration.orchestration_metrics import get_metrics_collector, DebateMetrics
from src.orchestration.production_orchestrator import ProductionOrchestrationService

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class EdgeCasePattern:
    """Detected edge case pattern."""
    id: str
    pattern_type: str
    description: str
    frequency: int
    severity: AlertLevel
    first_seen: datetime
    last_seen: datetime
    examples: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceInsight:
    """Performance insight or recommendation."""
    category: str
    title: str
    description: str
    impact: str  # "high", "medium", "low"
    confidence: float  # 0.0 to 1.0
    data_points: int
    recommendations: List[str] = field(default_factory=list)
    supporting_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemAlert:
    """System alert for anomalies or issues."""
    id: str
    alert_type: str
    level: AlertLevel
    title: str
    message: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    actions_taken: List[str] = field(default_factory=list)


class EdgeCaseDetector:
    """Detects edge cases and anomalous patterns in debate orchestration."""
    
    def __init__(self, metrics_collector):
        self.metrics_collector = metrics_collector
        self.detected_patterns: Dict[str, EdgeCasePattern] = {}
        self.pattern_history: List[EdgeCasePattern] = []
        
        # Detection thresholds
        self.thresholds = {
            'high_error_rate': 0.1,  # 10% error rate
            'long_debate_duration': 1800,  # 30 minutes
            'low_consensus_rate': 0.3,  # 30% consensus rate
            'high_escalation_rate': 0.2,  # 20% escalation rate
            'unusual_argument_count': (1, 50),  # Min 1, Max 50 arguments
            'template_failure_rate': 0.15  # 15% template failure rate
        }
    
    def analyze_patterns(self) -> List[EdgeCasePattern]:
        """Analyze metrics for edge case patterns."""
        patterns = []
        
        # Get debate metrics
        debate_metrics = list(self.metrics_collector.debate_metrics.values())
        if not debate_metrics:
            return patterns
        
        # Detect high error rate patterns
        patterns.extend(self._detect_error_patterns(debate_metrics))
        
        # Detect unusual duration patterns
        patterns.extend(self._detect_duration_patterns(debate_metrics))
        
        # Detect consensus issues
        patterns.extend(self._detect_consensus_patterns(debate_metrics))
        
        # Detect escalation patterns
        patterns.extend(self._detect_escalation_patterns(debate_metrics))
        
        # Detect argument count anomalies
        patterns.extend(self._detect_argument_patterns(debate_metrics))
        
        # Update pattern tracking
        self._update_pattern_tracking(patterns)
        
        return patterns
    
    def _detect_error_patterns(self, debate_metrics: List[DebateMetrics]) -> List[EdgeCasePattern]:
        """Detect patterns related to high error rates."""
        patterns = []
        
        # Calculate error rate
        total_debates = len(debate_metrics)
        error_debates = [m for m in debate_metrics if m.error_count > 0]
        error_rate = len(error_debates) / total_debates if total_debates > 0 else 0
        
        if error_rate > self.thresholds['high_error_rate']:
            # Analyze error types
            error_details = []
            for metrics in error_debates:
                error_details.append(f"Debate {metrics.debate_id}: {metrics.error_count} errors")
            
            pattern = EdgeCasePattern(
                id="high_error_rate",
                pattern_type="error_analysis",
                description=f"High error rate detected: {error_rate:.1%}",
                frequency=len(error_debates),
                severity=AlertLevel.ERROR if error_rate > 0.2 else AlertLevel.WARNING,
                first_seen=min(m.start_time for m in error_debates),
                last_seen=max(m.end_time for m in error_debates if m.end_time),
                examples=error_details[:5],
                suggested_actions=[
                    "Review error logs for common failure patterns",
                    "Check AI client connectivity and rate limits",
                    "Verify rule configurations for edge cases",
                    "Consider adding retry logic for failed operations"
                ],
                metadata={'error_rate': error_rate, 'total_debates': total_debates}
            )
            patterns.append(pattern)
        
        return patterns
    
    def _detect_duration_patterns(self, debate_metrics: List[DebateMetrics]) -> List[EdgeCasePattern]:
        """Detect patterns related to unusual debate durations."""
        patterns = []
        
        # Get completed debates with duration
        completed_debates = [m for m in debate_metrics if m.end_time and m.duration]
        if not completed_debates:
            return patterns
        
        durations = [m.duration.total_seconds() for m in completed_debates]
        avg_duration = statistics.mean(durations)
        
        # Find unusually long debates
        long_debates = [m for m in completed_debates 
                       if m.duration.total_seconds() > self.thresholds['long_debate_duration']]
        
        if long_debates:
            pattern = EdgeCasePattern(
                id="long_debate_duration",
                pattern_type="performance_analysis",
                description=f"Detected {len(long_debates)} debates with unusually long duration",
                frequency=len(long_debates),
                severity=AlertLevel.WARNING,
                first_seen=min(m.start_time for m in long_debates),
                last_seen=max(m.end_time for m in long_debates),
                examples=[
                    f"Debate {m.debate_id}: {m.duration.total_seconds():.0f}s ({m.total_rounds} rounds)"
                    for m in long_debates[:3]
                ],
                suggested_actions=[
                    "Review timeout configurations",
                    "Analyze if specific topics cause longer debates",
                    "Consider optimizing AI response times",
                    "Check for stuck workflows"
                ],
                metadata={
                    'avg_duration_seconds': avg_duration,
                    'long_duration_threshold': self.thresholds['long_debate_duration'],
                    'max_duration_seconds': max(durations)
                }
            )
            patterns.append(pattern)
        
        return patterns
    
    def _detect_consensus_patterns(self, debate_metrics: List[DebateMetrics]) -> List[EdgeCasePattern]:
        """Detect patterns related to consensus issues."""
        patterns = []
        
        completed_debates = [m for m in debate_metrics if m.end_time]
        if not completed_debates:
            return patterns
        
        consensus_debates = [m for m in completed_debates if m.consensus_reached]
        consensus_rate = len(consensus_debates) / len(completed_debates)
        
        if consensus_rate < self.thresholds['low_consensus_rate']:
            no_consensus_debates = [m for m in completed_debates if not m.consensus_reached]
            
            pattern = EdgeCasePattern(
                id="low_consensus_rate",
                pattern_type="consensus_analysis",
                description=f"Low consensus rate detected: {consensus_rate:.1%}",
                frequency=len(no_consensus_debates),
                severity=AlertLevel.WARNING,
                first_seen=min(m.start_time for m in no_consensus_debates),
                last_seen=max(m.end_time for m in no_consensus_debates),
                examples=[
                    f"Debate {m.debate_id}: {m.total_rounds} rounds, no consensus"
                    for m in no_consensus_debates[:3]
                ],
                suggested_actions=[
                    "Review consensus detection thresholds",
                    "Analyze debate topics for controversial subjects",
                    "Consider adjusting participant instructions",
                    "Review template effectiveness"
                ],
                metadata={
                    'consensus_rate': consensus_rate,
                    'total_completed': len(completed_debates),
                    'avg_confidence': statistics.mean([m.consensus_confidence for m in consensus_debates]) if consensus_debates else 0
                }
            )
            patterns.append(pattern)
        
        return patterns
    
    def _detect_escalation_patterns(self, debate_metrics: List[DebateMetrics]) -> List[EdgeCasePattern]:
        """Detect patterns related to escalations."""
        patterns = []
        
        escalated_debates = [m for m in debate_metrics if m.escalated]
        total_debates = len(debate_metrics)
        
        if total_debates == 0:
            return patterns
        
        escalation_rate = len(escalated_debates) / total_debates
        
        if escalation_rate > self.thresholds['high_escalation_rate']:
            pattern = EdgeCasePattern(
                id="high_escalation_rate",
                pattern_type="escalation_analysis",
                description=f"High escalation rate detected: {escalation_rate:.1%}",
                frequency=len(escalated_debates),
                severity=AlertLevel.WARNING,
                first_seen=min(m.start_time for m in escalated_debates),
                last_seen=max(m.end_time for m in escalated_debates if m.end_time),
                examples=[
                    f"Debate {m.debate_id}: escalated after {m.total_rounds} rounds"
                    for m in escalated_debates[:3]
                ],
                suggested_actions=[
                    "Review escalation triggers and thresholds",
                    "Analyze topics that frequently require escalation",
                    "Consider improving automated resolution",
                    "Train additional human moderators"
                ],
                metadata={
                    'escalation_rate': escalation_rate,
                    'total_debates': total_debates
                }
            )
            patterns.append(pattern)
        
        return patterns
    
    def _detect_argument_patterns(self, debate_metrics: List[DebateMetrics]) -> List[EdgeCasePattern]:
        """Detect patterns related to unusual argument counts."""
        patterns = []
        
        if not debate_metrics:
            return patterns
        
        argument_counts = [m.total_arguments for m in debate_metrics]
        min_threshold, max_threshold = self.thresholds['unusual_argument_count']
        
        # Detect very low argument counts
        low_arg_debates = [m for m in debate_metrics if m.total_arguments <= min_threshold]
        if low_arg_debates:
            pattern = EdgeCasePattern(
                id="low_argument_count",
                pattern_type="engagement_analysis",
                description=f"Detected {len(low_arg_debates)} debates with very few arguments",
                frequency=len(low_arg_debates),
                severity=AlertLevel.WARNING,
                first_seen=min(m.start_time for m in low_arg_debates),
                last_seen=max(m.end_time for m in low_arg_debates if m.end_time),
                examples=[
                    f"Debate {m.debate_id}: only {m.total_arguments} arguments"
                    for m in low_arg_debates[:3]
                ],
                suggested_actions=[
                    "Check for AI client failures",
                    "Review debate prompts for clarity",
                    "Verify participant configurations",
                    "Check for early termination conditions"
                ]
            )
            patterns.append(pattern)
        
        # Detect very high argument counts
        high_arg_debates = [m for m in debate_metrics if m.total_arguments >= max_threshold]
        if high_arg_debates:
            pattern = EdgeCasePattern(
                id="high_argument_count",
                pattern_type="engagement_analysis",
                description=f"Detected {len(high_arg_debates)} debates with excessive arguments",
                frequency=len(high_arg_debates),
                severity=AlertLevel.INFO,
                first_seen=min(m.start_time for m in high_arg_debates),
                last_seen=max(m.end_time for m in high_arg_debates if m.end_time),
                examples=[
                    f"Debate {m.debate_id}: {m.total_arguments} arguments in {m.total_rounds} rounds"
                    for m in high_arg_debates[:3]
                ],
                suggested_actions=[
                    "Review maximum rounds configuration",
                    "Check for repetitive arguments",
                    "Consider stricter consensus thresholds",
                    "Analyze debate complexity settings"
                ]
            )
            patterns.append(pattern)
        
        return patterns
    
    def _update_pattern_tracking(self, new_patterns: List[EdgeCasePattern]):
        """Update pattern tracking with new detections."""
        for pattern in new_patterns:
            if pattern.id in self.detected_patterns:
                # Update existing pattern
                existing = self.detected_patterns[pattern.id]
                existing.frequency += pattern.frequency
                existing.last_seen = pattern.last_seen
                existing.examples.extend(pattern.examples)
                
                # Keep only recent examples
                existing.examples = existing.examples[-10:]
            else:
                # New pattern
                self.detected_patterns[pattern.id] = pattern
                self.pattern_history.append(pattern)


class PerformanceAnalyzer:
    """Analyzes system performance and provides insights."""
    
    def __init__(self, metrics_collector):
        self.metrics_collector = metrics_collector
    
    def generate_insights(self) -> List[PerformanceInsight]:
        """Generate performance insights and recommendations."""
        insights = []
        
        # Analyze debate duration patterns
        insights.extend(self._analyze_duration_efficiency())
        
        # Analyze template effectiveness
        insights.extend(self._analyze_template_performance())
        
        # Analyze consensus patterns
        insights.extend(self._analyze_consensus_effectiveness())
        
        # Analyze resource utilization
        insights.extend(self._analyze_resource_utilization())
        
        return insights
    
    def _analyze_duration_efficiency(self) -> List[PerformanceInsight]:
        """Analyze debate duration efficiency."""
        insights = []
        
        debate_metrics = list(self.metrics_collector.debate_metrics.values())
        completed_debates = [m for m in debate_metrics if m.end_time and m.duration]
        
        if len(completed_debates) < 10:  # Need sufficient data
            return insights
        
        durations = [m.duration.total_seconds() for m in completed_debates]
        avg_duration = statistics.mean(durations)
        median_duration = statistics.median(durations)
        
        # Check if average is significantly higher than median (indicates outliers)
        if avg_duration > median_duration * 1.5:
            insight = PerformanceInsight(
                category="efficiency",
                title="Duration Outliers Detected",
                description=f"Average duration ({avg_duration:.0f}s) is significantly higher than median ({median_duration:.0f}s), indicating some debates are taking much longer than expected.",
                impact="medium",
                confidence=0.8,
                data_points=len(completed_debates),
                recommendations=[
                    "Identify topics or templates causing longer debates",
                    "Review timeout configurations",
                    "Consider implementing debate length warnings",
                    "Optimize AI response times"
                ],
                supporting_data={
                    'avg_duration': avg_duration,
                    'median_duration': median_duration,
                    'max_duration': max(durations),
                    'std_deviation': statistics.stdev(durations)
                }
            )
            insights.append(insight)
        
        return insights
    
    def _analyze_template_performance(self) -> List[PerformanceInsight]:
        """Analyze template performance and effectiveness."""
        insights = []
        
        # This would require template usage tracking in metrics
        # For now, provide a general insight
        
        debate_metrics = list(self.metrics_collector.debate_metrics.values())
        if not debate_metrics:
            return insights
        
        completion_rate = len([m for m in debate_metrics if m.completed_successfully]) / len(debate_metrics)
        
        if completion_rate < 0.9:  # Less than 90% completion rate
            insight = PerformanceInsight(
                category="reliability",
                title="Template Completion Rate",
                description=f"Template completion rate is {completion_rate:.1%}, indicating potential issues with debate workflows.",
                impact="high",
                confidence=0.9,
                data_points=len(debate_metrics),
                recommendations=[
                    "Review failed debate logs for common patterns",
                    "Validate template configurations",
                    "Check AI client reliability",
                    "Implement better error recovery"
                ],
                supporting_data={
                    'completion_rate': completion_rate,
                    'total_debates': len(debate_metrics),
                    'failed_debates': len([m for m in debate_metrics if not m.completed_successfully])
                }
            )
            insights.append(insight)
        
        return insights
    
    def _analyze_consensus_effectiveness(self) -> List[PerformanceInsight]:
        """Analyze consensus reaching effectiveness."""
        insights = []
        
        debate_metrics = list(self.metrics_collector.debate_metrics.values())
        completed_debates = [m for m in debate_metrics if m.end_time]
        
        if len(completed_debates) < 5:
            return insights
        
        consensus_debates = [m for m in completed_debates if m.consensus_reached]
        consensus_rate = len(consensus_debates) / len(completed_debates)
        
        if consensus_rate > 0.8:  # High consensus rate
            insight = PerformanceInsight(
                category="effectiveness",
                title="High Consensus Achievement",
                description=f"System achieves consensus in {consensus_rate:.1%} of debates, indicating effective orchestration.",
                impact="high",
                confidence=0.9,
                data_points=len(completed_debates),
                recommendations=[
                    "Document successful patterns for replication",
                    "Share templates with other systems",
                    "Consider reducing debate duration for high-consensus topics"
                ],
                supporting_data={
                    'consensus_rate': consensus_rate,
                    'avg_confidence': statistics.mean([m.consensus_confidence for m in consensus_debates]) if consensus_debates else 0
                }
            )
            insights.append(insight)
        elif consensus_rate < 0.5:  # Low consensus rate
            insight = PerformanceInsight(
                category="effectiveness",
                title="Low Consensus Achievement",
                description=f"System only achieves consensus in {consensus_rate:.1%} of debates, suggesting improvement opportunities.",
                impact="high",
                confidence=0.9,
                data_points=len(completed_debates),
                recommendations=[
                    "Review consensus detection thresholds",
                    "Analyze participant instruction effectiveness",
                    "Consider topic complexity assessment",
                    "Implement consensus facilitation techniques"
                ],
                supporting_data={
                    'consensus_rate': consensus_rate,
                    'total_completed': len(completed_debates)
                }
            )
            insights.append(insight)
        
        return insights
    
    def _analyze_resource_utilization(self) -> List[PerformanceInsight]:
        """Analyze resource utilization patterns."""
        insights = []
        
        # Get system metrics
        system_metrics = self.metrics_collector.get_summary_stats()
        
        if 'system' in system_metrics:
            metrics_collected = system_metrics['system'].get('metrics_collected', 0)
            events_logged = system_metrics['system'].get('events_logged', 0)
            
            if metrics_collected > 10000:  # High metrics volume
                insight = PerformanceInsight(
                    category="performance",
                    title="High Metrics Volume",
                    description=f"System has collected {metrics_collected} metrics, consider optimizing collection frequency.",
                    impact="low",
                    confidence=0.7,
                    data_points=1,
                    recommendations=[
                        "Review metrics collection frequency",
                        "Implement metrics sampling for high-volume events",
                        "Set up metrics archival strategy",
                        "Consider real-time vs batch processing"
                    ],
                    supporting_data={
                        'metrics_collected': metrics_collected,
                        'events_logged': events_logged
                    }
                )
                insights.append(insight)
        
        return insights


class AnalyticsDashboard:
    """Analytics dashboard for orchestration system monitoring."""
    
    def __init__(self, orchestration_service: ProductionOrchestrationService):
        self.orchestration_service = orchestration_service
        self.metrics_collector = get_metrics_collector()
        self.edge_case_detector = EdgeCaseDetector(self.metrics_collector)
        self.performance_analyzer = PerformanceAnalyzer(self.metrics_collector)
        
        self.alerts: List[SystemAlert] = []
        self.app = FastAPI(title="Orchestration Analytics Dashboard", version="1.0.0")
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes for analytics dashboard."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home():
            """Main analytics dashboard."""
            return self._render_dashboard()
        
        @self.app.get("/api/edge-cases")
        async def get_edge_cases():
            """Get detected edge case patterns."""
            patterns = self.edge_case_detector.analyze_patterns()
            return [asdict(pattern) for pattern in patterns]
        
        @self.app.get("/api/insights")
        async def get_performance_insights():
            """Get performance insights and recommendations."""
            insights = self.performance_analyzer.generate_insights()
            return [asdict(insight) for insight in insights]
        
        @self.app.get("/api/alerts")
        async def get_system_alerts():
            """Get system alerts."""
            return [asdict(alert) for alert in self.alerts[-50:]]  # Last 50 alerts
        
        @self.app.get("/api/metrics/summary")
        async def get_metrics_summary():
            """Get metrics summary."""
            return self.metrics_collector.get_summary_stats()
        
        @self.app.get("/api/debates/analysis")
        async def get_debate_analysis():
            """Get debate analysis data."""
            return self._generate_debate_analysis()
        
        @self.app.get("/api/system/health")
        async def get_system_health():
            """Get system health status."""
            return self.orchestration_service.get_system_status()
    
    def _render_dashboard(self) -> str:
        """Render the analytics dashboard HTML."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Orchestration Analytics Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .card h3 { margin-top: 0; color: #333; }
        .metric { text-align: center; padding: 15px; }
        .metric-value { font-size: 2em; font-weight: bold; color: #007bff; }
        .metric-label { color: #666; font-size: 0.9em; }
        .alert { padding: 10px; margin: 5px 0; border-radius: 4px; }
        .alert-warning { background: #fff3cd; border-left: 4px solid #ffc107; }
        .alert-error { background: #f8d7da; border-left: 4px solid #dc3545; }
        .alert-info { background: #d4edda; border-left: 4px solid #28a745; }
        .chart-container { height: 300px; margin: 10px 0; }
        .table { width: 100%; border-collapse: collapse; }
        .table th, .table td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        .table th { background: #f8f9fa; }
        .badge { padding: 2px 6px; border-radius: 3px; font-size: 0.8em; }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-warning { background: #fff3cd; color: #856404; }
        .badge-danger { background: #f8d7da; color: #721c24; }
        .refresh-btn { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Orchestration Analytics Dashboard</h1>
            <p>Real-time monitoring and insights for debate orchestration system</p>
            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>📈 System Overview</h3>
                <div id="system-metrics"></div>
            </div>
            
            <div class="card">
                <h3>⚠️ Edge Cases & Alerts</h3>
                <div id="edge-cases"></div>
            </div>
            
            <div class="card">
                <h3>💡 Performance Insights</h3>
                <div id="insights"></div>
            </div>
            
            <div class="card">
                <h3>📊 Debate Analysis</h3>
                <div id="debate-chart" class="chart-container"></div>
            </div>
            
            <div class="card">
                <h3>🎯 Pattern Detection</h3>
                <div id="patterns"></div>
            </div>
            
            <div class="card">
                <h3>⚡ Recent Activity</h3>
                <div id="recent-alerts"></div>
            </div>
        </div>
    </div>

    <script>
        async function loadData() {
            try {
                const [health, edgeCases, insights, analysis, alerts] = await Promise.all([
                    fetch('/api/system/health').then(r => r.json()),
                    fetch('/api/edge-cases').then(r => r.json()),
                    fetch('/api/insights').then(r => r.json()),
                    fetch('/api/debates/analysis').then(r => r.json()),
                    fetch('/api/alerts').then(r => r.json())
                ]);
                
                updateSystemMetrics(health);
                updateEdgeCases(edgeCases);
                updateInsights(insights);
                updateDebateChart(analysis);
                updateAlerts(alerts);
                
            } catch (error) {
                console.error('Error loading data:', error);
            }
        }
        
        function updateSystemMetrics(health) {
            const html = `
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px;">
                    <div class="metric">
                        <div class="metric-value">${health.active_debates || 0}</div>
                        <div class="metric-label">Active Debates</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${health.total_templates || 0}</div>
                        <div class="metric-label">Templates</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${health.status === 'running' ? '✅' : '❌'}</div>
                        <div class="metric-label">Status</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${Math.round((health.uptime_seconds || 0) / 3600)}h</div>
                        <div class="metric-label">Uptime</div>
                    </div>
                </div>
            `;
            document.getElementById('system-metrics').innerHTML = html;
        }
        
        function updateEdgeCases(edgeCases) {
            if (edgeCases.length === 0) {
                document.getElementById('edge-cases').innerHTML = '<p>No edge cases detected</p>';
                return;
            }
            
            const html = edgeCases.map(ec => `
                <div class="alert alert-${ec.severity}">
                    <strong>${ec.pattern_type}:</strong> ${ec.description}
                    <br><small>Frequency: ${ec.frequency}, Last seen: ${new Date(ec.last_seen).toLocaleString()}</small>
                </div>
            `).join('');
            
            document.getElementById('edge-cases').innerHTML = html;
        }
        
        function updateInsights(insights) {
            if (insights.length === 0) {
                document.getElementById('insights').innerHTML = '<p>No insights available</p>';
                return;
            }
            
            const html = insights.map(insight => `
                <div class="alert alert-info">
                    <strong>${insight.title}</strong>
                    <p>${insight.description}</p>
                    <small>Impact: ${insight.impact}, Confidence: ${(insight.confidence * 100).toFixed()}%</small>
                </div>
            `).join('');
            
            document.getElementById('insights').innerHTML = html;
        }
        
        function updateDebateChart(analysis) {
            // Simple bar chart showing debate distribution
            const data = [{
                x: analysis.categories || ['Simple', 'Standard', 'Complex'],
                y: analysis.counts || [0, 0, 0],
                type: 'bar',
                marker: { color: ['#28a745', '#007bff', '#dc3545'] }
            }];
            
            const layout = {
                title: 'Debate Distribution by Type',
                xaxis: { title: 'Template Type' },
                yaxis: { title: 'Count' },
                height: 250
            };
            
            Plotly.newPlot('debate-chart', data, layout, {responsive: true});
        }
        
        function updateAlerts(alerts) {
            if (alerts.length === 0) {
                document.getElementById('recent-alerts').innerHTML = '<p>No recent alerts</p>';
                return;
            }
            
            const html = alerts.slice(-5).map(alert => `
                <div class="alert alert-${alert.level}">
                    <strong>${alert.alert_type}:</strong> ${alert.message}
                    <br><small>${new Date(alert.created_at).toLocaleString()}</small>
                </div>
            `).join('');
            
            document.getElementById('recent-alerts').innerHTML = html;
        }
        
        function refreshData() {
            loadData();
        }
        
        // Load data on page load
        loadData();
        
        // Auto-refresh every 30 seconds
        setInterval(loadData, 30000);
    </script>
</body>
</html>
        """
    
    def _generate_debate_analysis(self) -> Dict[str, Any]:
        """Generate debate analysis data for charts."""
        debate_metrics = list(self.metrics_collector.debate_metrics.values())
        
        # Simple analysis for demo
        categories = ['Simple', 'Standard', 'Complex']
        counts = [0, 0, 0]  # Would be calculated based on actual data
        
        return {
            'categories': categories,
            'counts': counts,
            'total_debates': len(debate_metrics),
            'completed_debates': len([m for m in debate_metrics if m.end_time]),
            'consensus_rate': len([m for m in debate_metrics if m.consensus_reached]) / max(len(debate_metrics), 1)
        }
    
    def generate_alert(
        self,
        alert_type: str,
        level: AlertLevel,
        title: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a system alert."""
        alert = SystemAlert(
            id=f"{alert_type}_{int(datetime.now().timestamp())}",
            alert_type=alert_type,
            level=level,
            title=title,
            message=message,
            created_at=datetime.now(),
            context=context or {}
        )
        
        self.alerts.append(alert)
        logger.warning(f"Alert generated: {title} - {message}")
        
        return alert.id


def create_analytics_dashboard(orchestration_service: ProductionOrchestrationService) -> AnalyticsDashboard:
    """Create an analytics dashboard for the orchestration service."""
    return AnalyticsDashboard(orchestration_service)