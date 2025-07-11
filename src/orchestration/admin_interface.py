"""
Admin Interface for Orchestration Rules Management

This module provides a web-based admin interface for managing orchestration rules,
viewing metrics, and monitoring active debates.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.orchestration.rules_engine import (
    DebateRule, RuleCondition, RuleAction, RuleConditionType, RuleActionType,
    StandardRuleFactory
)
from src.orchestration.event_driven_orchestrator import EventDrivenOrchestrator
from src.orchestration.orchestration_metrics import get_metrics_collector, MetricType, LogLevel

logger = logging.getLogger(__name__)


# Pydantic models for API
class RuleConditionModel(BaseModel):
    type: RuleConditionType
    field: str
    value: Any
    operator: str = "and"


class RuleActionModel(BaseModel):
    type: RuleActionType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0


class DebateRuleModel(BaseModel):
    id: str
    name: str
    description: str
    conditions: List[RuleConditionModel]
    actions: List[RuleActionModel]
    enabled: bool = True
    priority: int = 0
    tags: List[str] = Field(default_factory=list)


class RuleUpdateModel(BaseModel):
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class OrchestrationAdminInterface:
    """Admin interface for orchestration management."""
    
    def __init__(self, orchestrator: EventDrivenOrchestrator):
        self.orchestrator = orchestrator
        self.metrics_collector = get_metrics_collector()
        self.app = FastAPI(title="Debate Orchestration Admin", version="1.0.0")
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def admin_dashboard():
            """Main admin dashboard."""
            return self._render_dashboard()
        
        @self.app.get("/api/rules", response_model=List[Dict[str, Any]])
        async def list_rules():
            """List all orchestration rules."""
            rules = []
            for rule in self.orchestrator.rules_engine.rules.values():
                rule_dict = {
                    'id': rule.id,
                    'name': rule.name,
                    'description': rule.description,
                    'enabled': rule.enabled,
                    'priority': rule.priority,
                    'tags': list(rule.tags),
                    'trigger_count': rule.trigger_count,
                    'last_triggered': rule.last_triggered.isoformat() if rule.last_triggered else None,
                    'created_at': rule.created_at.isoformat(),
                    'conditions_count': len(rule.conditions),
                    'actions_count': len(rule.actions)
                }
                rules.append(rule_dict)
            
            return sorted(rules, key=lambda r: r['priority'], reverse=True)
        
        @self.app.get("/api/rules/{rule_id}", response_model=Dict[str, Any])
        async def get_rule(rule_id: str):
            """Get detailed information about a specific rule."""
            rule = self.orchestrator.rules_engine.rules.get(rule_id)
            if not rule:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            return {
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'enabled': rule.enabled,
                'priority': rule.priority,
                'tags': list(rule.tags),
                'trigger_count': rule.trigger_count,
                'last_triggered': rule.last_triggered.isoformat() if rule.last_triggered else None,
                'created_at': rule.created_at.isoformat(),
                'conditions': [
                    {
                        'type': cond.type.value,
                        'field': cond.field,
                        'value': cond.value,
                        'operator': cond.operator
                    } for cond in rule.conditions
                ],
                'actions': [
                    {
                        'type': action.type.value,
                        'parameters': action.parameters,
                        'priority': action.priority
                    } for action in rule.actions
                ]
            }
        
        @self.app.post("/api/rules", response_model=Dict[str, Any])
        async def create_rule(rule_data: DebateRuleModel):
            """Create a new orchestration rule."""
            try:
                # Convert Pydantic model to DebateRule
                conditions = [
                    RuleCondition(
                        type=cond.type,
                        field=cond.field,
                        value=cond.value,
                        operator=cond.operator
                    ) for cond in rule_data.conditions
                ]
                
                actions = [
                    RuleAction(
                        type=action.type,
                        parameters=action.parameters,
                        priority=action.priority
                    ) for action in rule_data.actions
                ]
                
                rule = DebateRule(
                    id=rule_data.id,
                    name=rule_data.name,
                    description=rule_data.description,
                    conditions=conditions,
                    actions=actions,
                    enabled=rule_data.enabled,
                    priority=rule_data.priority,
                    tags=set(rule_data.tags)
                )
                
                self.orchestrator.add_custom_rule(rule)
                
                return {"message": f"Rule '{rule_data.name}' created successfully", "rule_id": rule_data.id}
                
            except Exception as e:
                logger.error(f"Error creating rule: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.put("/api/rules/{rule_id}", response_model=Dict[str, Any])
        async def update_rule(rule_id: str, update_data: RuleUpdateModel):
            """Update a rule's properties."""
            rule = self.orchestrator.rules_engine.rules.get(rule_id)
            if not rule:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            if update_data.enabled is not None:
                rule.enabled = update_data.enabled
            
            if update_data.priority is not None:
                rule.priority = update_data.priority
            
            return {"message": f"Rule '{rule_id}' updated successfully"}
        
        @self.app.delete("/api/rules/{rule_id}", response_model=Dict[str, Any])
        async def delete_rule(rule_id: str):
            """Delete a rule."""
            success = self.orchestrator.rules_engine.remove_rule(rule_id)
            if not success:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            return {"message": f"Rule '{rule_id}' deleted successfully"}
        
        @self.app.post("/api/rules/{rule_id}/enable", response_model=Dict[str, Any])
        async def enable_rule(rule_id: str):
            """Enable a rule."""
            success = self.orchestrator.rules_engine.enable_rule(rule_id)
            if not success:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            return {"message": f"Rule '{rule_id}' enabled"}
        
        @self.app.post("/api/rules/{rule_id}/disable", response_model=Dict[str, Any])
        async def disable_rule(rule_id: str):
            """Disable a rule."""
            success = self.orchestrator.rules_engine.disable_rule(rule_id)
            if not success:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            return {"message": f"Rule '{rule_id}' disabled"}
        
        @self.app.get("/api/metrics", response_model=Dict[str, Any])
        async def get_metrics():
            """Get orchestration metrics."""
            return self.metrics_collector.get_summary_stats()
        
        @self.app.get("/api/metrics/rules", response_model=Dict[str, Any])
        async def get_rule_metrics():
            """Get rule performance metrics."""
            return self.metrics_collector.get_rule_performance()
        
        @self.app.get("/api/sessions", response_model=List[Dict[str, Any]])
        async def list_active_sessions():
            """List active orchestration sessions."""
            sessions = []
            for session in self.orchestrator.get_active_sessions():
                session_dict = {
                    'id': str(session.id),
                    'debate_id': str(session.debate_id),
                    'state': session.state.value,
                    'start_time': session.start_time.isoformat(),
                    'last_action_time': session.last_action_time.isoformat() if session.last_action_time else None,
                    'applied_template': session.applied_template,
                    'context': {
                        'round_count': session.context.round_count,
                        'argument_count': session.context.argument_count,
                        'participant_count': session.context.participant_count,
                        'complexity': session.context.complexity,
                        'consensus_indicators': session.context.consensus_indicators
                    }
                }
                sessions.append(session_dict)
            
            return sessions
        
        @self.app.get("/api/sessions/{session_id}", response_model=Dict[str, Any])
        async def get_session(session_id: str):
            """Get detailed information about a session."""
            try:
                session_uuid = UUID(session_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid session ID format")
            
            # Find session by ID
            session = None
            for s in self.orchestrator.get_active_sessions():
                if s.id == session_uuid:
                    session = s
                    break
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            debate_metrics = self.metrics_collector.get_debate_metrics(session.debate_id)
            
            return {
                'id': str(session.id),
                'debate_id': str(session.debate_id),
                'state': session.state.value,
                'start_time': session.start_time.isoformat(),
                'last_action_time': session.last_action_time.isoformat() if session.last_action_time else None,
                'applied_template': session.applied_template,
                'context': {
                    'round_count': session.context.round_count,
                    'argument_count': session.context.argument_count,
                    'participant_count': session.context.participant_count,
                    'complexity': session.context.complexity,
                    'consensus_indicators': session.context.consensus_indicators,
                    'custom_variables': session.context.custom_variables
                },
                'metrics': {
                    'total_rounds': debate_metrics.total_rounds if debate_metrics else 0,
                    'total_arguments': debate_metrics.total_arguments if debate_metrics else 0,
                    'rules_triggered': debate_metrics.rules_triggered if debate_metrics else [],
                    'error_count': debate_metrics.error_count if debate_metrics else 0
                }
            }
        
        @self.app.get("/api/templates", response_model=List[Dict[str, Any]])
        async def list_templates():
            """List available debate templates."""
            templates = []
            for template_id, template in self.orchestrator.template_registry.items():
                template_dict = {
                    'id': template.id,
                    'name': template.name,
                    'description': template.description,
                    'version': template.version,
                    'participants': template.participants,
                    'max_rounds': template.config.max_rounds,
                    'consensus_threshold': template.config.consensus_threshold,
                    'created_at': template.created_at.isoformat()
                }
                templates.append(template_dict)
            
            return templates
        
        @self.app.post("/api/rules/reload-standard", response_model=Dict[str, Any])
        async def reload_standard_rules():
            """Reload standard rules."""
            try:
                # Clear existing standard rules
                standard_rule_ids = [
                    "start_new_round", "complete_on_consensus", "complete_max_rounds",
                    "pause_idle", "escalate_complex", "simple_template", "complex_template"
                ]
                
                for rule_id in standard_rule_ids:
                    self.orchestrator.rules_engine.remove_rule(rule_id)
                
                # Reload standard rules
                standard_rules = StandardRuleFactory.create_all_standard_rules()
                for rule in standard_rules:
                    self.orchestrator.rules_engine.add_rule(rule)
                
                return {"message": f"Reloaded {len(standard_rules)} standard rules"}
                
            except Exception as e:
                logger.error(f"Error reloading standard rules: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/events", response_model=List[Dict[str, Any]])
        async def get_recent_events(limit: int = 50):
            """Get recent orchestration events."""
            events = self.metrics_collector.events[-limit:]
            return [
                {
                    'event_id': event.event_id,
                    'event_type': event.event_type,
                    'debate_id': str(event.debate_id),
                    'timestamp': event.timestamp.isoformat(),
                    'level': event.level.value,
                    'message': event.message,
                    'duration_ms': event.duration_ms,
                    'rule_id': event.rule_id,
                    'action_type': event.action_type
                } for event in events
            ]
    
    def _render_dashboard(self) -> str:
        """Render the admin dashboard HTML."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Debate Orchestration Admin</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .nav {{
            background: #333;
            padding: 0;
            display: flex;
        }}
        .nav-item {{
            flex: 1;
            text-align: center;
            padding: 15px;
            color: white;
            cursor: pointer;
            transition: background 0.3s;
        }}
        .nav-item:hover, .nav-item.active {{
            background: #555;
        }}
        .content {{
            padding: 20px;
            min-height: 600px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 20px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 5px;
        }}
        .metric-label {{
            color: #6c757d;
            font-size: 0.9em;
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .table th, .table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        .table th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        .badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 500;
        }}
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        .badge-danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        .badge-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        .btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            margin: 2px;
        }}
        .btn-primary {{
            background: #007bff;
            color: white;
        }}
        .btn-success {{
            background: #28a745;
            color: white;
        }}
        .btn-danger {{
            background: #dc3545;
            color: white;
        }}
        .hidden {{
            display: none;
        }}
        #loading {{
            text-align: center;
            padding: 50px;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Debate Orchestration Admin</h1>
            <p>Event-Driven Rules Engine Management</p>
        </div>
        
        <div class="nav">
            <div class="nav-item active" onclick="showTab('overview')">Overview</div>
            <div class="nav-item" onclick="showTab('rules')">Rules</div>
            <div class="nav-item" onclick="showTab('sessions')">Active Sessions</div>
            <div class="nav-item" onclick="showTab('metrics')">Metrics</div>
            <div class="nav-item" onclick="showTab('events')">Events</div>
        </div>
        
        <div class="content">
            <div id="loading">Loading...</div>
            
            <div id="overview-tab" class="tab-content hidden">
                <h2>System Overview</h2>
                <div id="overview-metrics" class="metrics-grid"></div>
                <div id="overview-summary"></div>
            </div>
            
            <div id="rules-tab" class="tab-content hidden">
                <h2>Orchestration Rules</h2>
                <div style="margin-bottom: 20px;">
                    <button class="btn btn-primary" onclick="reloadStandardRules()">Reload Standard Rules</button>
                    <button class="btn btn-success" onclick="createNewRule()">Create New Rule</button>
                </div>
                <div id="rules-table"></div>
            </div>
            
            <div id="sessions-tab" class="tab-content hidden">
                <h2>Active Orchestration Sessions</h2>
                <div id="sessions-table"></div>
            </div>
            
            <div id="metrics-tab" class="tab-content hidden">
                <h2>Performance Metrics</h2>
                <div id="metrics-details"></div>
            </div>
            
            <div id="events-tab" class="tab-content hidden">
                <h2>Recent Events</h2>
                <div id="events-table"></div>
            </div>
        </div>
    </div>

    <script>
        let currentTab = 'overview';
        
        async function loadData() {{
            document.getElementById('loading').style.display = 'block';
            
            try {{
                const [metrics, rules, sessions] = await Promise.all([
                    fetch('/api/metrics').then(r => r.json()),
                    fetch('/api/rules').then(r => r.json()),
                    fetch('/api/sessions').then(r => r.json())
                ]);
                
                updateOverview(metrics, rules, sessions);
                updateRulesTable(rules);
                updateSessionsTable(sessions);
                updateMetricsDetails(metrics);
                
                document.getElementById('loading').style.display = 'none';
                showTab(currentTab);
                
            }} catch (error) {{
                console.error('Error loading data:', error);
                document.getElementById('loading').innerHTML = 'Error loading data. Please refresh the page.';
            }}
        }}
        
        function showTab(tabName) {{
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {{
                tab.classList.add('hidden');
            }});
            
            // Remove active class from nav items
            document.querySelectorAll('.nav-item').forEach(item => {{
                item.classList.remove('active');
            }});
            
            // Show selected tab
            document.getElementById(tabName + '-tab').classList.remove('hidden');
            event.target.classList.add('active');
            
            currentTab = tabName;
            
            // Load specific data for some tabs
            if (tabName === 'events') {{
                loadEvents();
            }}
        }}
        
        function updateOverview(metrics, rules, sessions) {{
            const activeRules = rules.filter(r => r.enabled).length;
            const activeSessions = sessions.length;
            
            document.getElementById('overview-metrics').innerHTML = `
                <div class="metric-card">
                    <div class="metric-value">${{activeRules}}</div>
                    <div class="metric-label">Active Rules</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${{activeSessions}}</div>
                    <div class="metric-label">Active Sessions</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${{metrics.debates?.completed || 0}}</div>
                    <div class="metric-label">Completed Debates</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${{Math.round((metrics.averages?.consensus_rate || 0) * 100)}}%</div>
                    <div class="metric-label">Consensus Rate</div>
                </div>
            `;
        }}
        
        function updateRulesTable(rules) {{
            const tableHtml = `
                <table class="table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Status</th>
                            <th>Priority</th>
                            <th>Triggers</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${{rules.map(rule => `
                            <tr>
                                <td><strong>${{rule.name}}</strong><br><small>${{rule.description}}</small></td>
                                <td><span class="badge badge-${{rule.enabled ? 'success' : 'danger'}}">${{rule.enabled ? 'Enabled' : 'Disabled'}}</span></td>
                                <td>${{rule.priority}}</td>
                                <td>${{rule.trigger_count}}</td>
                                <td>
                                    <button class="btn ${{rule.enabled ? 'btn-danger' : 'btn-success'}}" onclick="toggleRule('${{rule.id}}', ${{!rule.enabled}})">
                                        ${{rule.enabled ? 'Disable' : 'Enable'}}
                                    </button>
                                </td>
                            </tr>
                        `).join('')}}
                    </tbody>
                </table>
            `;
            document.getElementById('rules-table').innerHTML = tableHtml;
        }}
        
        function updateSessionsTable(sessions) {{
            if (sessions.length === 0) {{
                document.getElementById('sessions-table').innerHTML = '<p>No active sessions</p>';
                return;
            }}
            
            const tableHtml = `
                <table class="table">
                    <thead>
                        <tr>
                            <th>Debate ID</th>
                            <th>State</th>
                            <th>Complexity</th>
                            <th>Rounds</th>
                            <th>Arguments</th>
                            <th>Started</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${{sessions.map(session => `
                            <tr>
                                <td>${{session.debate_id.substring(0, 8)}}...</td>
                                <td><span class="badge badge-${{session.state === 'active' ? 'success' : 'warning'}}">${{session.state}}</span></td>
                                <td>${{session.context.complexity}}</td>
                                <td>${{session.context.round_count}}</td>
                                <td>${{session.context.argument_count}}</td>
                                <td>${{new Date(session.start_time).toLocaleString()}}</td>
                            </tr>
                        `).join('')}}
                    </tbody>
                </table>
            `;
            document.getElementById('sessions-table').innerHTML = tableHtml;
        }}
        
        function updateMetricsDetails(metrics) {{
            document.getElementById('metrics-details').innerHTML = `
                <h3>System Metrics</h3>
                <pre>${{JSON.stringify(metrics, null, 2)}}</pre>
            `;
        }}
        
        async function loadEvents() {{
            try {{
                const events = await fetch('/api/events').then(r => r.json());
                
                const tableHtml = `
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Type</th>
                                <th>Level</th>
                                <th>Message</th>
                                <th>Rule</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${{events.map(event => `
                                <tr>
                                    <td>${{new Date(event.timestamp).toLocaleString()}}</td>
                                    <td>${{event.event_type}}</td>
                                    <td><span class="badge badge-${{event.level === 'error' ? 'danger' : event.level === 'warning' ? 'warning' : 'success'}}">${{event.level}}</span></td>
                                    <td>${{event.message}}</td>
                                    <td>${{event.rule_id || '-'}}</td>
                                </tr>
                            `).join('')}}
                        </tbody>
                    </table>
                `;
                document.getElementById('events-table').innerHTML = tableHtml;
                
            }} catch (error) {{
                console.error('Error loading events:', error);
                document.getElementById('events-table').innerHTML = '<p>Error loading events</p>';
            }}
        }}
        
        async function toggleRule(ruleId, enable) {{
            try {{
                const endpoint = enable ? 'enable' : 'disable';
                await fetch(`/api/rules/${{ruleId}}/${{endpoint}}`, {{ method: 'POST' }});
                loadData(); // Reload to show changes
            }} catch (error) {{
                console.error('Error toggling rule:', error);
                alert('Error updating rule');
            }}
        }}
        
        async function reloadStandardRules() {{
            try {{
                await fetch('/api/rules/reload-standard', {{ method: 'POST' }});
                loadData(); // Reload to show changes
                alert('Standard rules reloaded successfully');
            }} catch (error) {{
                console.error('Error reloading rules:', error);
                alert('Error reloading standard rules');
            }}
        }}
        
        function createNewRule() {{
            alert('Rule creation interface coming soon!');
        }}
        
        // Load data on page load
        loadData();
        
        // Auto-refresh every 30 seconds
        setInterval(loadData, 30000);
    </script>
</body>
</html>
        """


def create_admin_app(orchestrator: EventDrivenOrchestrator) -> FastAPI:
    """Create the admin interface FastAPI app."""
    admin = OrchestrationAdminInterface(orchestrator)
    return admin.app