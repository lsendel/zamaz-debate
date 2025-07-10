"""
Evolution Effectiveness Dashboard

Provides a web interface for viewing evolution effectiveness metrics and insights.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .domain_services import EvolutionEffectivenessService, MetricsCollectionService
from .repositories import (
    JsonEvolutionEffectivenessRepository, 
    JsonMetricsRepository,
    EvolutionEffectivenessReportRepository,
    EvolutionEffectivenessQueryService
)


class EvolutionEffectivenessDashboard:
    """
    Dashboard for visualizing evolution effectiveness data
    """
    
    def __init__(self, data_dir: str = "data"):
        self.effectiveness_repo = JsonEvolutionEffectivenessRepository()
        self.metrics_repo = JsonMetricsRepository()
        self.reports_repo = EvolutionEffectivenessReportRepository()
        self.query_service = EvolutionEffectivenessQueryService(
            self.effectiveness_repo,
            self.metrics_repo,
            self.reports_repo
        )
        self.effectiveness_service = EvolutionEffectivenessService(data_dir)
        self.metrics_service = MetricsCollectionService(data_dir)
    
    async def get_dashboard_data(self) -> Dict:
        """Get comprehensive dashboard data"""
        dashboard_data = {
            "summary": await self.get_effectiveness_summary(),
            "recent_assessments": await self.get_recent_assessments(),
            "concerning_patterns": await self.get_concerning_patterns(),
            "health_metrics": await self.get_system_health_metrics(),
            "effectiveness_trends": await self.get_effectiveness_trends(),
            "generated_at": datetime.now().isoformat()
        }
        
        return dashboard_data
    
    async def get_effectiveness_summary(self) -> Dict:
        """Get summary of evolution effectiveness"""
        return await self.query_service.get_effectiveness_summary()
    
    async def get_recent_assessments(self, limit: int = 10) -> List[Dict]:
        """Get recent evolution effectiveness assessments"""
        all_effectiveness = await self.effectiveness_repo.find_all()
        
        # Sort by creation date (most recent first)
        sorted_effectiveness = sorted(
            all_effectiveness,
            key=lambda e: e.creation_date,
            reverse=True
        )
        
        recent_assessments = []
        for effectiveness in sorted_effectiveness[:limit]:
            assessment_data = {
                "evolution_id": effectiveness.evolution_id,
                "status": effectiveness.status.value,
                "creation_date": effectiveness.creation_date.isoformat(),
                "latest_score": None,
                "effectiveness_level": None,
                "issues_count": 0,
                "recommendations_count": 0
            }
            
            if effectiveness.effectiveness_scores:
                latest_score = effectiveness.effectiveness_scores[-1]
                assessment_data.update({
                    "latest_score": latest_score.overall_score,
                    "effectiveness_level": latest_score.effectiveness_level.value,
                    "confidence": latest_score.confidence
                })
            
            if effectiveness.validation_results:
                latest_validation = effectiveness.validation_results[-1]
                assessment_data.update({
                    "issues_count": len(latest_validation.issues_found),
                    "recommendations_count": len(latest_validation.recommendations)
                })
            
            recent_assessments.append(assessment_data)
        
        return recent_assessments
    
    async def get_concerning_patterns(self) -> List[Dict]:
        """Get concerning evolution patterns"""
        # Load evolution history
        evolution_history = await self._load_evolution_history()
        
        # Detect patterns
        patterns = await self.effectiveness_service.detect_evolution_patterns(evolution_history)
        
        return [
            {
                "pattern_type": pattern.pattern_type,
                "description": pattern.description,
                "occurrences": pattern.occurrences,
                "risk_level": pattern.risk_level,
                "recommendation": pattern.recommendation,
                "is_concerning": pattern.is_concerning()
            }
            for pattern in patterns
        ]
    
    async def get_system_health_metrics(self) -> Dict:
        """Get overall system health metrics"""
        evolution_history = await self._load_evolution_history()
        health = await self.effectiveness_service.assess_evolution_health(evolution_history)
        
        return {
            "effectiveness_trend": health.effectiveness_trend,
            "repetition_risk": health.repetition_risk,
            "technical_debt_level": health.technical_debt_level,
            "diversity_score": health.diversity_score,
            "last_effective_evolution": health.last_effective_evolution,
            "health_score": health.get_health_score(),
            "is_healthy": health.is_healthy(),
            "concerning_patterns_count": len(health.concerning_patterns)
        }
    
    async def get_effectiveness_trends(self) -> Dict:
        """Get effectiveness trends over time"""
        all_effectiveness = await self.effectiveness_repo.find_all()
        
        if not all_effectiveness:
            return {
                "trend_data": [],
                "average_score_trend": "stable",
                "improvement_rate": 0.0
            }
        
        # Sort by creation date
        sorted_effectiveness = sorted(all_effectiveness, key=lambda e: e.creation_date)
        
        trend_data = []
        for effectiveness in sorted_effectiveness:
            if effectiveness.effectiveness_scores:
                latest_score = effectiveness.effectiveness_scores[-1]
                trend_data.append({
                    "date": effectiveness.creation_date.isoformat()[:10],  # YYYY-MM-DD
                    "evolution_id": effectiveness.evolution_id,
                    "score": latest_score.overall_score,
                    "effectiveness_level": latest_score.effectiveness_level.value
                })
        
        # Calculate trend
        if len(trend_data) >= 3:
            recent_scores = [item["score"] for item in trend_data[-5:]]
            early_scores = [item["score"] for item in trend_data[:5]]
            
            recent_avg = sum(recent_scores) / len(recent_scores)
            early_avg = sum(early_scores) / len(early_scores)
            
            if recent_avg > early_avg + 5:
                trend = "improving"
            elif recent_avg < early_avg - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend_data": trend_data,
            "average_score_trend": trend,
            "improvement_rate": 0.0  # Could calculate this more precisely
        }
    
    async def get_evolution_details(self, evolution_id: str) -> Dict:
        """Get detailed information about a specific evolution"""
        return await self.query_service.get_evolution_timeline(evolution_id)
    
    async def get_problematic_evolutions(self) -> List[Dict]:
        """Get list of evolutions with problems"""
        return await self.query_service.find_problematic_evolutions()
    
    async def _load_evolution_history(self) -> List[Dict]:
        """Load evolution history from the existing system"""
        from pathlib import Path
        
        evolution_history_file = Path("data/evolutions/evolution_history.json")
        
        if not evolution_history_file.exists():
            return []
        
        try:
            with open(evolution_history_file, 'r') as f:
                data = json.load(f)
                return data.get("evolutions", [])
        except Exception:
            return []
    
    def render_dashboard_html(self, dashboard_data: Dict) -> str:
        """Render dashboard data as HTML"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Evolution Effectiveness Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f4f4f4; padding: 20px; margin-bottom: 20px; }}
                .summary {{ display: flex; gap: 20px; margin-bottom: 20px; }}
                .metric-card {{ background: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 5px; flex: 1; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
                .metric-label {{ color: #666; font-size: 14px; }}
                .section {{ margin-bottom: 30px; }}
                .section h2 {{ border-bottom: 2px solid #333; padding-bottom: 5px; }}
                .health-score {{ font-size: 20px; padding: 10px; border-radius: 5px; }}
                .health-good {{ background: #d4edda; color: #155724; }}
                .health-warning {{ background: #fff3cd; color: #856404; }}
                .health-danger {{ background: #f8d7da; color: #721c24; }}
                .assessment-item {{ background: #f9f9f9; margin: 10px 0; padding: 15px; border-left: 4px solid #007bff; }}
                .pattern-item {{ background: #fff; border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                .pattern-high {{ border-left: 4px solid #dc3545; }}
                .pattern-medium {{ border-left: 4px solid #ffc107; }}
                .pattern-low {{ border-left: 4px solid #28a745; }}
                .timestamp {{ color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Evolution Effectiveness Dashboard</h1>
                <p class="timestamp">Generated at: {dashboard_data['generated_at']}</p>
            </div>
            
            <div class="summary">
                <div class="metric-card">
                    <div class="metric-value">{dashboard_data['summary']['total_assessments']}</div>
                    <div class="metric-label">Total Assessments</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{dashboard_data['summary']['effectiveness_rate']:.1f}%</div>
                    <div class="metric-label">Effectiveness Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{dashboard_data['summary']['average_score']:.1f}</div>
                    <div class="metric-label">Average Score</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{dashboard_data['summary']['rolled_back_count']}</div>
                    <div class="metric-label">Rolled Back</div>
                </div>
            </div>
            
            <div class="section">
                <h2>System Health</h2>
                <div class="health-score {'health-good' if dashboard_data['health_metrics']['is_healthy'] else 'health-warning'}">
                    Health Score: {dashboard_data['health_metrics']['health_score']:.1f}/100
                    <br>Status: {'Healthy' if dashboard_data['health_metrics']['is_healthy'] else 'Needs Attention'}
                    <br>Trend: {dashboard_data['health_metrics']['effectiveness_trend'].title()}
                    <br>Repetition Risk: {dashboard_data['health_metrics']['repetition_risk']:.2f}
                    <br>Technical Debt: {dashboard_data['health_metrics']['technical_debt_level'].title()}
                    <br>Diversity Score: {dashboard_data['health_metrics']['diversity_score']:.2f}
                </div>
            </div>
            
            <div class="section">
                <h2>Concerning Patterns</h2>
                {''.join([f'''
                <div class="pattern-item pattern-{pattern['risk_level']}">
                    <strong>{pattern['pattern_type'].replace('_', ' ').title()}</strong> (Risk: {pattern['risk_level'].title()})
                    <br>{pattern['description']}
                    <br><em>Recommendation: {pattern['recommendation']}</em>
                    <br>Occurrences: {pattern['occurrences']}
                </div>
                ''' for pattern in dashboard_data['concerning_patterns']])}
            </div>
            
            <div class="section">
                <h2>Recent Assessments</h2>
                {''.join([f'''
                <div class="assessment-item">
                    <strong>Evolution: {assessment['evolution_id']}</strong>
                    <br>Status: {assessment['status'].title()}
                    <br>Score: {assessment['latest_score'] or 'N/A'}
                    <br>Level: {assessment.get('effectiveness_level', 'N/A').replace('_', ' ').title()}
                    <br>Issues: {assessment['issues_count']}, Recommendations: {assessment['recommendations_count']}
                    <br>Created: {assessment['creation_date'][:10]}
                </div>
                ''' for assessment in dashboard_data['recent_assessments'][:5]])}
            </div>
        </body>
        </html>
        """
        
        return html