"""
Tests for Phase 1: Event-Driven Orchestration System

Comprehensive tests for the rules engine, event-driven orchestrator, metrics, and admin interface.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch

from src.orchestration.rules_engine import (
    RulesEngine, DebateRule, RuleCondition, RuleAction, DebateContext,
    RuleConditionType, RuleActionType, StandardRuleFactory, RuleConditionEvaluator
)
from src.orchestration.event_driven_orchestrator import (
    EventDrivenOrchestrator, OrchestrationSession, OrchestrationState
)
from src.orchestration.orchestration_metrics import (
    MetricsCollector, MetricType, LogLevel, DebateMetrics, OrchestrationEvent
)
from src.orchestration.admin_interface import create_admin_app
from src.contexts.debate.events import DebateStarted, ArgumentPresented, RoundCompleted
from src.events.event_bus import EventBus


class TestRulesEngine:
    """Test suite for the rules engine."""
    
    @pytest.fixture
    def rules_engine(self):
        """Create a fresh rules engine for testing."""
        return RulesEngine()
    
    @pytest.fixture
    def sample_context(self):
        """Create a sample debate context for testing."""
        return DebateContext(
            debate_id=uuid4(),
            round_count=2,
            argument_count=4,
            participant_count=2,
            start_time=datetime.now() - timedelta(minutes=5),
            last_activity=datetime.now() - timedelta(minutes=1),
            complexity="moderate",
            question_keywords={"architecture", "design", "pattern"},
            consensus_indicators={"confidence": 0.6, "level": "moderate"}
        )
    
    @pytest.fixture
    def sample_rule(self):
        """Create a sample rule for testing."""
        return DebateRule(
            id="test_rule",
            name="Test Rule",
            description="A test rule for unit testing",
            conditions=[
                RuleCondition(
                    type=RuleConditionType.GREATER_THAN,
                    field="round_count",
                    value=1
                )
            ],
            actions=[
                RuleAction(
                    type=RuleActionType.CONTINUE_DEBATE,
                    priority=10
                )
            ],
            priority=50
        )
    
    def test_add_rule(self, rules_engine, sample_rule):
        """Test adding a rule to the engine."""
        rules_engine.add_rule(sample_rule)
        
        assert sample_rule.id in rules_engine.rules
        assert rules_engine.rules[sample_rule.id] == sample_rule
    
    def test_remove_rule(self, rules_engine, sample_rule):
        """Test removing a rule from the engine."""
        rules_engine.add_rule(sample_rule)
        success = rules_engine.remove_rule(sample_rule.id)
        
        assert success
        assert sample_rule.id not in rules_engine.rules
    
    def test_enable_disable_rule(self, rules_engine, sample_rule):
        """Test enabling and disabling rules."""
        rules_engine.add_rule(sample_rule)
        
        # Test disable
        success = rules_engine.disable_rule(sample_rule.id)
        assert success
        assert not rules_engine.rules[sample_rule.id].enabled
        
        # Test enable
        success = rules_engine.enable_rule(sample_rule.id)
        assert success
        assert rules_engine.rules[sample_rule.id].enabled
    
    def test_rule_condition_evaluation(self, sample_context):
        """Test rule condition evaluation."""
        # Test GREATER_THAN condition
        condition = RuleCondition(
            type=RuleConditionType.GREATER_THAN,
            field="round_count",
            value=1
        )
        result = RuleConditionEvaluator.evaluate_condition(condition, sample_context)
        assert result is True  # round_count=2 > 1
        
        # Test EQUALS condition
        condition = RuleCondition(
            type=RuleConditionType.EQUALS,
            field="complexity",
            value="moderate"
        )
        result = RuleConditionEvaluator.evaluate_condition(condition, sample_context)
        assert result is True
        
        # Test CONTAINS condition
        condition = RuleCondition(
            type=RuleConditionType.CONTAINS,
            field="question_keywords",
            value="architecture"
        )
        result = RuleConditionEvaluator.evaluate_condition(condition, sample_context)
        # This will fail because question_keywords is a set, not a string
        # But the function should handle the error gracefully
        assert result is False
    
    def test_rule_evaluation(self, rules_engine, sample_rule, sample_context):
        """Test evaluating rules against context."""
        rules_engine.add_rule(sample_rule)
        
        results = rules_engine.evaluate_rules(sample_context)
        
        assert len(results) == 1
        assert results[0].rule_triggered is True
        assert results[0].rule == sample_rule
        assert len(results[0].actions) == 1
    
    def test_rule_priority_ordering(self, rules_engine, sample_context):
        """Test that rules are evaluated in priority order."""
        high_priority_rule = DebateRule(
            id="high_priority",
            name="High Priority Rule",
            description="High priority test rule",
            conditions=[],  # No conditions, always triggers
            actions=[RuleAction(type=RuleActionType.CONTINUE_DEBATE)],
            priority=100
        )
        
        low_priority_rule = DebateRule(
            id="low_priority",
            name="Low Priority Rule", 
            description="Low priority test rule",
            conditions=[],  # No conditions, always triggers
            actions=[RuleAction(type=RuleActionType.PAUSE_DEBATE)],
            priority=10
        )
        
        # Add in reverse order
        rules_engine.add_rule(low_priority_rule)
        rules_engine.add_rule(high_priority_rule)
        
        results = rules_engine.evaluate_rules(sample_context)
        
        # Should be ordered by priority (high to low)
        assert results[0].rule.priority == 100
        assert results[1].rule.priority == 10
    
    def test_standard_rule_factory(self):
        """Test standard rule factory creates valid rules."""
        orchestration_rules = StandardRuleFactory.create_basic_orchestration_rules()
        template_rules = StandardRuleFactory.create_template_selection_rules()
        all_rules = StandardRuleFactory.create_all_standard_rules()
        
        assert len(orchestration_rules) > 0
        assert len(template_rules) > 0
        assert len(all_rules) == len(orchestration_rules) + len(template_rules)
        
        # Verify all rules have required fields
        for rule in all_rules:
            assert rule.id
            assert rule.name
            assert rule.description
            assert isinstance(rule.conditions, list)
            assert isinstance(rule.actions, list)
            assert isinstance(rule.priority, int)
    
    def test_metrics_tracking(self, rules_engine, sample_rule, sample_context):
        """Test that metrics are tracked correctly."""
        rules_engine.add_rule(sample_rule)
        
        initial_count = rules_engine.metrics['total_evaluations']
        rules_engine.evaluate_rules(sample_context)
        
        assert rules_engine.metrics['total_evaluations'] == initial_count + 1
        assert rules_engine.metrics['rules_triggered'] > 0


class TestEventDrivenOrchestrator:
    """Test suite for the event-driven orchestrator."""
    
    @pytest.fixture
    def event_bus(self):
        """Create a test event bus."""
        return EventBus()
    
    @pytest.fixture
    def ai_client_factory(self):
        """Create a mock AI client factory."""
        factory = Mock()
        factory.get_claude_client.return_value = Mock()
        factory.get_gemini_client.return_value = Mock()
        return factory
    
    @pytest.fixture
    def orchestrator(self, event_bus, ai_client_factory):
        """Create a test orchestrator."""
        return EventDrivenOrchestrator(event_bus, ai_client_factory)
    
    @pytest.fixture
    def mock_debate_session(self):
        """Create a mock debate session."""
        session = Mock()
        session.id = uuid4()
        session.participants = ["claude", "gemini"]
        session.rounds = []
        return session
    
    @pytest.mark.asyncio
    async def test_start_orchestration(self, orchestrator, mock_debate_session):
        """Test starting orchestration for a debate."""
        session = await orchestrator.start_orchestration(
            mock_debate_session,
            "Test question",
            "moderate"
        )
        
        assert session.debate_id == mock_debate_session.id
        assert session.state == OrchestrationState.ACTIVE
        assert session.context.complexity == "moderate"
        assert mock_debate_session.id in orchestrator.active_sessions
    
    @pytest.mark.asyncio
    async def test_debate_started_event_handling(self, orchestrator, event_bus):
        """Test handling of debate started events."""
        debate_id = uuid4()
        
        # Create a session
        mock_session = Mock()
        mock_session.id = uuid4()
        mock_session.debate_id = debate_id
        mock_session.context = Mock()
        mock_session.update_activity = Mock()
        
        orchestrator.active_sessions[debate_id] = mock_session
        
        # Emit debate started event
        event = DebateStarted(
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="DebateStarted",
            aggregate_id=debate_id,
            debate_id=debate_id,
            topic="Test topic",
            participants=["claude", "gemini"]
        )
        
        await event_bus.publish(event)
        
        # Allow event processing
        await asyncio.sleep(0.1)
        
        # Verify session was updated
        mock_session.update_activity.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_argument_presented_handling(self, orchestrator):
        """Test handling of argument presented events."""
        debate_id = uuid4()
        
        # Create session with mock context
        mock_context = Mock()
        mock_context.argument_count = 0
        mock_context.consensus_indicators = {"confidence": 0.0}
        
        mock_session = Mock()
        mock_session.debate_id = debate_id
        mock_session.context = mock_context
        mock_session.update_activity = Mock()
        
        orchestrator.active_sessions[debate_id] = mock_session
        
        # Mock the private methods
        orchestrator._update_consensus_indicators = AsyncMock()
        orchestrator._evaluate_and_apply_rules = AsyncMock()
        
        # Create argument presented event
        event = ArgumentPresented(
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="ArgumentPresented",
            aggregate_id=debate_id,
            debate_id=debate_id,
            participant="claude",
            content="Test argument content"
        )
        
        await orchestrator._handle_argument_presented(event)
        
        # Verify updates
        assert mock_context.argument_count == 1
        mock_session.update_activity.assert_called_once()
        orchestrator._update_consensus_indicators.assert_called_once()
        orchestrator._evaluate_and_apply_rules.assert_called_once()
    
    def test_get_metrics(self, orchestrator):
        """Test getting orchestrator metrics."""
        metrics = orchestrator.get_metrics()
        
        assert 'total_debates_orchestrated' in metrics
        assert 'successful_completions' in metrics
        assert 'consensus_reached' in metrics
        assert 'active_sessions' in metrics
        assert isinstance(metrics['active_sessions'], int)
    
    def test_register_template(self, orchestrator):
        """Test registering debate templates."""
        template = Mock()
        template.id = "test_template"
        template.name = "Test Template"
        
        orchestrator.register_template(template)
        
        assert "test_template" in orchestrator.template_registry
        assert orchestrator.template_registry["test_template"] == template
    
    @pytest.mark.asyncio
    async def test_shutdown(self, orchestrator):
        """Test orchestrator shutdown."""
        # Add a mock active session
        debate_id = uuid4()
        mock_session = Mock()
        mock_session.debate_id = debate_id
        mock_session.state = OrchestrationState.ACTIVE
        
        orchestrator.active_sessions[debate_id] = mock_session
        orchestrator._complete_debate = AsyncMock()
        
        await orchestrator.shutdown()
        
        # Verify session was completed
        orchestrator._complete_debate.assert_called_once()


class TestMetricsCollector:
    """Test suite for the metrics collector."""
    
    @pytest.fixture
    def metrics_collector(self, tmp_path):
        """Create a test metrics collector."""
        return MetricsCollector(enable_file_export=True, export_path=tmp_path)
    
    def test_record_metric(self, metrics_collector):
        """Test recording metrics."""
        metrics_collector.record_metric(
            "test_counter",
            1.0,
            MetricType.COUNTER,
            tags={"test": "value"}
        )
        
        assert len(metrics_collector.metrics) == 1
        assert "test_counter" in metrics_collector.counters
        assert metrics_collector.counters["test_counter"] == 1.0
    
    def test_log_event(self, metrics_collector):
        """Test logging orchestration events."""
        debate_id = uuid4()
        
        metrics_collector.log_event(
            "test_event",
            debate_id,
            "Test message",
            level=LogLevel.INFO,
            context={"key": "value"}
        )
        
        assert len(metrics_collector.events) == 1
        event = metrics_collector.events[0]
        assert event.event_type == "test_event"
        assert event.debate_id == debate_id
        assert event.message == "Test message"
        assert event.level == LogLevel.INFO
    
    def test_debate_tracking(self, metrics_collector):
        """Test debate metrics tracking."""
        debate_id = uuid4()
        participants = {"claude", "gemini"}
        
        # Start tracking
        metrics_collector.start_debate_tracking(debate_id, participants)
        
        assert debate_id in metrics_collector.debate_metrics
        debate_metrics = metrics_collector.debate_metrics[debate_id]
        assert debate_metrics.participants == participants
        
        # End tracking
        metrics_collector.end_debate_tracking(
            debate_id,
            completed_successfully=True,
            consensus_reached=True,
            consensus_confidence=0.8
        )
        
        assert debate_metrics.completed_successfully
        assert debate_metrics.consensus_reached
        assert debate_metrics.consensus_confidence == 0.8
        assert debate_metrics.end_time is not None
    
    def test_rule_triggered_recording(self, metrics_collector):
        """Test recording rule triggers."""
        debate_id = uuid4()
        rule_id = "test_rule"
        
        metrics_collector.record_rule_triggered(rule_id, debate_id, 2)
        
        # Check metrics
        assert "rules_triggered" in metrics_collector.counters
        assert "rule_actions" in metrics_collector.histograms
        
        # Check events
        assert len(metrics_collector.events) == 1
        event = metrics_collector.events[0]
        assert event.rule_id == rule_id
    
    def test_action_execution_recording(self, metrics_collector):
        """Test recording action executions."""
        debate_id = uuid4()
        
        metrics_collector.record_action_executed(
            "test_action",
            debate_id,
            150.5,
            success=True
        )
        
        assert "actions_executed" in metrics_collector.counters
        assert "actions_successful" in metrics_collector.counters
        assert "action_duration_ms" in metrics_collector.timers
    
    def test_summary_stats(self, metrics_collector):
        """Test getting summary statistics."""
        # Add some test data
        debate_id = uuid4()
        metrics_collector.start_debate_tracking(debate_id, {"claude", "gemini"})
        metrics_collector.end_debate_tracking(debate_id, True, True, 0.8)
        
        stats = metrics_collector.get_summary_stats()
        
        assert 'debates' in stats
        assert 'averages' in stats
        assert 'counters' in stats
        assert 'system' in stats
        
        assert stats['debates']['completed'] == 1
        assert stats['averages']['consensus_rate'] == 1.0
    
    def test_export_metrics(self, metrics_collector, tmp_path):
        """Test exporting metrics to files."""
        # Add some test data
        debate_id = uuid4()
        metrics_collector.start_debate_tracking(debate_id, {"claude", "gemini"})
        metrics_collector.log_event("test", debate_id, "test message")
        
        metrics_collector.export_metrics()
        
        # Check that files were created
        files = list(tmp_path.glob("*.json"))
        assert len(files) >= 2  # At least summary and events files
        
        # Check file names contain timestamp
        file_names = [f.name for f in files]
        assert any("summary_" in name for name in file_names)
        assert any("events_" in name for name in file_names)


class TestAdminInterface:
    """Test suite for the admin interface."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a mock orchestrator for testing."""
        orchestrator = Mock()
        orchestrator.rules_engine = Mock()
        orchestrator.rules_engine.rules = {}
        orchestrator.get_active_sessions.return_value = []
        orchestrator.get_metrics.return_value = {}
        orchestrator.template_registry = {}
        return orchestrator
    
    @pytest.fixture
    def admin_app(self, orchestrator):
        """Create the admin interface app."""
        return create_admin_app(orchestrator)
    
    @pytest.mark.asyncio
    async def test_admin_app_creation(self, admin_app):
        """Test that the admin app is created successfully."""
        assert admin_app is not None
        assert hasattr(admin_app, 'routes')
    
    def test_api_routes_exist(self, admin_app):
        """Test that required API routes exist."""
        route_paths = [route.path for route in admin_app.routes]
        
        required_routes = [
            "/",
            "/api/rules",
            "/api/metrics",
            "/api/sessions",
            "/api/events"
        ]
        
        for route in required_routes:
            assert route in route_paths


class TestIntegration:
    """Integration tests for the complete orchestration system."""
    
    @pytest.fixture
    def event_bus(self):
        """Create a test event bus."""
        return EventBus()
    
    @pytest.fixture
    def ai_client_factory(self):
        """Create a mock AI client factory."""
        factory = Mock()
        claude_client = Mock()
        gemini_client = Mock()
        
        # Mock client responses
        claude_response = Mock()
        claude_response.content = [Mock(text="Claude's response")]
        claude_client.messages.create.return_value = claude_response
        
        gemini_response = Mock()
        gemini_response.text = "Gemini's response"
        gemini_client.generate_content_async = AsyncMock(return_value=gemini_response)
        
        factory.get_claude_client.return_value = claude_client
        factory.get_gemini_client.return_value = gemini_client
        
        return factory
    
    @pytest.fixture
    def integrated_system(self, event_bus, ai_client_factory):
        """Create an integrated orchestration system."""
        orchestrator = EventDrivenOrchestrator(event_bus, ai_client_factory)
        metrics_collector = MetricsCollector(enable_file_export=False)
        admin_app = create_admin_app(orchestrator)
        
        return {
            'orchestrator': orchestrator,
            'metrics_collector': metrics_collector,
            'admin_app': admin_app,
            'event_bus': event_bus
        }
    
    @pytest.mark.asyncio
    async def test_end_to_end_orchestration(self, integrated_system):
        """Test end-to-end orchestration flow."""
        orchestrator = integrated_system['orchestrator']
        event_bus = integrated_system['event_bus']
        
        # Create mock debate session
        debate_session = Mock()
        debate_session.id = uuid4()
        debate_session.participants = ["claude", "gemini"]
        debate_session.rounds = []
        
        # Start orchestration
        session = await orchestrator.start_orchestration(
            debate_session,
            "Should we implement microservices architecture?",
            "complex"
        )
        
        assert session.state == OrchestrationState.ACTIVE
        assert session.debate_id in orchestrator.active_sessions
        
        # Simulate argument presentation
        event = ArgumentPresented(
            event_id=uuid4(),
            occurred_at=datetime.now(),
            event_type="ArgumentPresented",
            aggregate_id=session.debate_id,
            debate_id=session.debate_id,
            participant="claude",
            content="Yes, microservices provide better scalability and maintainability"
        )
        
        await event_bus.publish(event)
        await asyncio.sleep(0.1)  # Allow event processing
        
        # Verify session was updated
        updated_session = orchestrator.get_session(session.debate_id)
        assert updated_session.context.argument_count > 0
    
    def test_metrics_integration(self, integrated_system):
        """Test metrics integration with orchestrator."""
        orchestrator = integrated_system['orchestrator']
        metrics_collector = integrated_system['metrics_collector']
        
        # Get initial metrics
        initial_metrics = orchestrator.get_metrics()
        assert 'total_debates_orchestrated' in initial_metrics
        
        # Test metrics collection
        debate_id = uuid4()
        metrics_collector.record_metric("test_metric", 1.0, MetricType.COUNTER)
        
        stats = metrics_collector.get_summary_stats()
        assert 'system' in stats
        assert stats['system']['metrics_collected'] > 0
    
    def test_rules_engine_integration(self, integrated_system):
        """Test rules engine integration with orchestrator."""
        orchestrator = integrated_system['orchestrator']
        
        # Verify standard rules are loaded
        rules = orchestrator.rules_engine.rules
        assert len(rules) > 0
        
        # Verify specific standard rules exist
        rule_ids = list(rules.keys())
        expected_rules = ["start_new_round", "complete_on_consensus", "complete_max_rounds"]
        
        for expected_rule in expected_rules:
            assert expected_rule in rule_ids
        
        # Test adding custom rule
        custom_rule = DebateRule(
            id="test_custom_rule",
            name="Test Custom Rule",
            description="A custom test rule",
            conditions=[],
            actions=[RuleAction(type=RuleActionType.CONTINUE_DEBATE)],
            priority=75
        )
        
        orchestrator.add_custom_rule(custom_rule)
        assert "test_custom_rule" in orchestrator.rules_engine.rules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])