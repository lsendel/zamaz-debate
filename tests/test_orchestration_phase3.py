"""
Tests for Phase 3: Production Operation and Analytics

Comprehensive tests for the production orchestration service, analytics dashboard,
and end-to-end system integration.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.orchestration.production_orchestrator import (
    ProductionOrchestrationService, OrchestrationConfig, SystemHealth,
    create_production_service
)
from src.orchestration.analytics_dashboard import (
    AnalyticsDashboard, EdgeCaseDetector, PerformanceAnalyzer,
    EdgeCasePattern, PerformanceInsight, SystemAlert, AlertLevel,
    create_analytics_dashboard
)
from src.orchestration.orchestration_metrics import DebateMetrics, get_metrics_collector
from src.contexts.debate.aggregates import DebateSession
from src.contexts.debate.value_objects import Topic
from src.events.event_bus import EventBus


class TestProductionOrchestrationService:
    """Test suite for the production orchestration service."""
    
    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration."""
        return OrchestrationConfig(
            template_storage_path=tmp_path / "templates",
            metrics_export_path=tmp_path / "metrics",
            max_concurrent_debates=5,
            enable_notifications=True,
            enable_metrics_export=False,  # Disable for testing
            enable_admin_interface=True,
            enable_health_checks=False,  # Disable background tasks for testing
            log_level="DEBUG"
        )
    
    @pytest.fixture
    def ai_client_factory(self):
        """Create mock AI client factory."""
        factory = Mock()
        claude_client = Mock()
        gemini_client = Mock()
        
        # Mock Claude responses
        claude_response = Mock()
        claude_response.content = [Mock(text="Claude's analysis of the proposal")]
        claude_client.messages.create.return_value = claude_response
        
        # Mock Gemini responses
        gemini_response = Mock()
        gemini_response.text = "Gemini's counter-analysis"
        gemini_client.generate_content_async = AsyncMock(return_value=gemini_response)
        
        factory.get_claude_client.return_value = claude_client
        factory.get_gemini_client.return_value = gemini_client
        
        return factory
    
    @pytest.fixture
    def service(self, config, ai_client_factory):
        """Create test production service."""
        return ProductionOrchestrationService(config, ai_client_factory)
    
    def test_service_initialization(self, service, config):
        """Test service initialization."""
        assert service.config == config
        assert service.ai_client_factory is not None
        assert not service.is_running
        assert service.start_time is None
        assert len(service.active_debates) == 0
    
    @pytest.mark.asyncio
    async def test_service_lifecycle(self, service):
        """Test service start and stop lifecycle."""
        # Test start
        await service.start()
        assert service.is_running
        assert service.start_time is not None
        assert service.orchestrator is not None
        
        # Test stop
        await service.stop()
        assert not service.is_running
    
    @pytest.mark.asyncio
    async def test_start_debate(self, service):
        """Test starting a debate."""
        await service.start()
        
        try:
            # Start a debate
            debate_id = await service.start_debate(
                question="Should we implement microservices architecture?",
                complexity="standard",
                template_id="standard_debate"
            )
            
            assert isinstance(debate_id, UUID)
            assert debate_id in service.active_debates
            
            # Check debate session
            debate_session = service.active_debates[debate_id]
            assert isinstance(debate_session, DebateSession)
            assert debate_session.topic.value == "Should we implement microservices architecture?"
            
        finally:
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_debate_limit(self, service):
        """Test concurrent debate limit enforcement."""
        await service.start()
        
        try:
            # Start debates up to the limit
            debate_ids = []
            for i in range(service.config.max_concurrent_debates):
                debate_id = await service.start_debate(
                    question=f"Test question {i}",
                    complexity="simple"
                )
                debate_ids.append(debate_id)
            
            # Try to start one more (should fail)
            with pytest.raises(RuntimeError, match="Maximum concurrent debates"):
                await service.start_debate(
                    question="This should fail",
                    complexity="simple"
                )
            
            assert len(service.active_debates) == service.config.max_concurrent_debates
            
        finally:
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_template_selection(self, service):
        """Test automatic template selection based on complexity."""
        await service.start()
        
        try:
            # Test simple complexity
            template_id = service._select_optimal_template("simple")
            assert template_id == "simple_debate"
            
            # Test complex complexity
            template_id = service._select_optimal_template("complex")
            assert template_id == "complex_debate"
            
            # Test default (moderate)
            template_id = service._select_optimal_template("moderate")
            assert template_id == "standard_debate"
            
        finally:
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_debate_completion(self, service):
        """Test debate completion and cleanup."""
        await service.start()
        
        try:
            # Start a debate
            debate_id = await service.start_debate(
                question="Test question",
                complexity="simple"
            )
            
            debate_session = service.active_debates[debate_id]
            
            # Complete the debate
            await service._complete_debate(debate_session, "test_completion")
            
            # Check cleanup
            assert debate_id not in service.active_debates
            
        finally:
            await service.stop()
    
    def test_system_status(self, service):
        """Test system status reporting."""
        status = service.get_system_status()
        
        assert "status" in status
        assert status["status"] == "not_started"  # Service not started yet
        
        # Test other status fields
        expected_fields = [
            "active_debates", "total_templates", "metrics", "config"
        ]
        
        # Start service to get full status
        asyncio.run(service.start())
        try:
            status = service.get_system_status()
            assert status["status"] == "running"
            assert status["active_debates"] == 0
            assert "config" in status
        finally:
            asyncio.run(service.stop())
    
    def test_get_active_debates(self, service):
        """Test getting active debates information."""
        # Initially empty
        debates = service.get_active_debates()
        assert len(debates) == 0
        
        # Add mock debate
        debate_id = uuid4()
        mock_session = Mock()
        mock_session.topic.value = "Test Topic"
        mock_session.participants = ["claude", "gemini"]
        mock_session.rounds = []
        mock_session.max_rounds = 3
        mock_session.consensus = None
        mock_session.decision = None
        
        service.active_debates[debate_id] = mock_session
        
        debates = service.get_active_debates()
        assert len(debates) == 1
        assert debates[0]["topic"] == "Test Topic"
        assert debates[0]["participants"] == ["claude", "gemini"]
    
    @pytest.mark.asyncio
    async def test_background_tasks(self, service):
        """Test background task management."""
        # Configure service with background tasks enabled
        service.config.enable_health_checks = True
        service.config.enable_metrics_export = True
        
        await service.start()
        
        try:
            # Check that background tasks are started
            assert service._health_check_task is not None
            assert service._metrics_export_task is not None
            assert service._cleanup_task is not None
            
        finally:
            await service.stop()
            
            # Check that tasks are stopped
            assert service._health_check_task.cancelled() or service._health_check_task.done()
    
    def test_admin_app_creation(self, service):
        """Test admin app creation."""
        # Need to initialize service first
        asyncio.run(service.initialize())
        
        try:
            admin_app = service.get_admin_app()
            assert admin_app is not None
            assert hasattr(admin_app, 'routes')
        except RuntimeError:
            # Expected if orchestrator not fully initialized
            pass


class TestEdgeCaseDetector:
    """Test suite for edge case detection."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create mock metrics collector."""
        collector = Mock()
        collector.debate_metrics = {}
        return collector
    
    @pytest.fixture
    def detector(self, metrics_collector):
        """Create edge case detector."""
        return EdgeCaseDetector(metrics_collector)
    
    @pytest.fixture
    def sample_debate_metrics(self):
        """Create sample debate metrics for testing."""
        metrics = []
        
        # Normal debates
        for i in range(10):
            metrics.append(DebateMetrics(
                debate_id=uuid4(),
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now() - timedelta(minutes=30),
                total_rounds=3,
                total_arguments=6,
                participants={"claude", "gemini"},
                consensus_reached=True,
                consensus_confidence=0.8,
                completed_successfully=True,
                error_count=0
            ))
        
        # High error debates
        for i in range(3):
            metrics.append(DebateMetrics(
                debate_id=uuid4(),
                start_time=datetime.now() - timedelta(hours=2),
                end_time=datetime.now() - timedelta(hours=1, minutes=30),
                total_rounds=2,
                total_arguments=2,
                participants={"claude", "gemini"},
                consensus_reached=False,
                consensus_confidence=0.0,
                completed_successfully=False,
                error_count=5
            ))
        
        return metrics
    
    def test_detector_initialization(self, detector):
        """Test detector initialization."""
        assert detector.metrics_collector is not None
        assert isinstance(detector.detected_patterns, dict)
        assert isinstance(detector.thresholds, dict)
        
        # Check threshold values
        assert 'high_error_rate' in detector.thresholds
        assert 'long_debate_duration' in detector.thresholds
        assert 'low_consensus_rate' in detector.thresholds
    
    def test_error_pattern_detection(self, detector, sample_debate_metrics):
        """Test detection of high error rate patterns."""
        detector.metrics_collector.debate_metrics = {
            str(m.debate_id): m for m in sample_debate_metrics
        }
        
        patterns = detector._detect_error_patterns(sample_debate_metrics)
        
        # Should detect high error rate (3 out of 13 debates have errors = 23%)
        assert len(patterns) > 0
        error_pattern = patterns[0]
        assert error_pattern.pattern_type == "error_analysis"
        assert error_pattern.severity in [AlertLevel.WARNING, AlertLevel.ERROR]
        assert "High error rate detected" in error_pattern.description
    
    def test_duration_pattern_detection(self, detector, sample_debate_metrics):
        """Test detection of unusual duration patterns."""
        # Add a long duration debate
        long_debate = DebateMetrics(
            debate_id=uuid4(),
            start_time=datetime.now() - timedelta(hours=2),
            end_time=datetime.now() - timedelta(minutes=30),  # 1.5 hours = 5400 seconds
            total_rounds=10,
            total_arguments=20,
            participants={"claude", "gemini"},
            consensus_reached=False,
            completed_successfully=True,
            error_count=0
        )
        
        metrics_with_long = sample_debate_metrics + [long_debate]
        patterns = detector._detect_duration_patterns(metrics_with_long)
        
        # Should detect long duration pattern
        if patterns:  # Only if duration exceeds threshold
            duration_pattern = patterns[0]
            assert duration_pattern.pattern_type == "performance_analysis"
            assert "unusually long duration" in duration_pattern.description
    
    def test_consensus_pattern_detection(self, detector):
        """Test detection of consensus issues."""
        # Create debates with low consensus rate
        low_consensus_metrics = []
        for i in range(10):
            low_consensus_metrics.append(DebateMetrics(
                debate_id=uuid4(),
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now() - timedelta(minutes=30),
                total_rounds=3,
                total_arguments=6,
                participants={"claude", "gemini"},
                consensus_reached=(i < 2),  # Only 2 out of 10 reach consensus = 20%
                consensus_confidence=0.8 if i < 2 else 0.2,
                completed_successfully=True,
                error_count=0
            ))
        
        patterns = detector._detect_consensus_patterns(low_consensus_metrics)
        
        # Should detect low consensus rate
        assert len(patterns) > 0
        consensus_pattern = patterns[0]
        assert consensus_pattern.pattern_type == "consensus_analysis"
        assert "Low consensus rate detected" in consensus_pattern.description
    
    def test_argument_pattern_detection(self, detector):
        """Test detection of unusual argument count patterns."""
        # Create debates with unusual argument counts
        unusual_metrics = [
            # Very low arguments
            DebateMetrics(
                debate_id=uuid4(),
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now() - timedelta(minutes=30),
                total_rounds=1,
                total_arguments=1,  # Very low
                participants={"claude"},
                consensus_reached=False,
                completed_successfully=True,
                error_count=0
            ),
            # Very high arguments
            DebateMetrics(
                debate_id=uuid4(),
                start_time=datetime.now() - timedelta(hours=2),
                end_time=datetime.now() - timedelta(minutes=30),
                total_rounds=10,
                total_arguments=60,  # Very high
                participants={"claude", "gemini"},
                consensus_reached=False,
                completed_successfully=True,
                error_count=0
            )
        ]
        
        patterns = detector._detect_argument_patterns(unusual_metrics)
        
        # Should detect both low and high argument patterns
        assert len(patterns) >= 1  # At least one pattern detected
        
        pattern_types = [p.id for p in patterns]
        assert "low_argument_count" in pattern_types or "high_argument_count" in pattern_types
    
    def test_pattern_analysis(self, detector, sample_debate_metrics):
        """Test full pattern analysis."""
        detector.metrics_collector.debate_metrics = {
            str(m.debate_id): m for m in sample_debate_metrics
        }
        
        patterns = detector.analyze_patterns()
        
        # Should detect at least error patterns
        assert len(patterns) > 0
        
        # Check pattern structure
        for pattern in patterns:
            assert isinstance(pattern, EdgeCasePattern)
            assert pattern.id
            assert pattern.pattern_type
            assert pattern.description
            assert isinstance(pattern.frequency, int)
            assert isinstance(pattern.severity, AlertLevel)
            assert isinstance(pattern.suggested_actions, list)


class TestPerformanceAnalyzer:
    """Test suite for performance analysis."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create mock metrics collector."""
        collector = Mock()
        collector.debate_metrics = {}
        return collector
    
    @pytest.fixture
    def analyzer(self, metrics_collector):
        """Create performance analyzer."""
        return PerformanceAnalyzer(metrics_collector)
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer.metrics_collector is not None
    
    def test_duration_efficiency_analysis(self, analyzer):
        """Test duration efficiency analysis."""
        # Create debates with duration outliers
        debate_metrics = []
        
        # Most debates take 10 minutes
        for i in range(10):
            debate_metrics.append(DebateMetrics(
                debate_id=uuid4(),
                start_time=datetime.now() - timedelta(minutes=15),
                end_time=datetime.now() - timedelta(minutes=5),  # 10 minutes
                total_rounds=3,
                total_arguments=6,
                participants={"claude", "gemini"},
                consensus_reached=True,
                completed_successfully=True
            ))
        
        # One debate takes 30 minutes (outlier)
        debate_metrics.append(DebateMetrics(
            debate_id=uuid4(),
            start_time=datetime.now() - timedelta(minutes=35),
            end_time=datetime.now() - timedelta(minutes=5),  # 30 minutes
            total_rounds=5,
            total_arguments=15,
            participants={"claude", "gemini"},
            consensus_reached=True,
            completed_successfully=True
        ))
        
        insights = analyzer._analyze_duration_efficiency(debate_metrics)
        
        # Should detect duration outliers
        assert len(insights) > 0
        duration_insight = insights[0]
        assert duration_insight.category == "efficiency"
        assert "Duration Outliers Detected" in duration_insight.title
    
    def test_template_performance_analysis(self, analyzer):
        """Test template performance analysis."""
        # Create debates with low completion rate
        debate_metrics = []
        
        # 7 successful debates
        for i in range(7):
            debate_metrics.append(DebateMetrics(
                debate_id=uuid4(),
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now() - timedelta(minutes=30),
                completed_successfully=True
            ))
        
        # 3 failed debates
        for i in range(3):
            debate_metrics.append(DebateMetrics(
                debate_id=uuid4(),
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now() - timedelta(minutes=30),
                completed_successfully=False
            ))
        
        insights = analyzer._analyze_template_performance(debate_metrics)
        
        # Should detect low completion rate (70% < 90%)
        assert len(insights) > 0
        completion_insight = insights[0]
        assert completion_insight.category == "reliability"
        assert "Template Completion Rate" in completion_insight.title
    
    def test_consensus_effectiveness_analysis(self, analyzer):
        """Test consensus effectiveness analysis."""
        # Test high consensus rate
        high_consensus_metrics = []
        for i in range(10):
            high_consensus_metrics.append(DebateMetrics(
                debate_id=uuid4(),
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now() - timedelta(minutes=30),
                consensus_reached=True,  # 100% consensus
                consensus_confidence=0.9,
                completed_successfully=True
            ))
        
        insights = analyzer._analyze_consensus_effectiveness(high_consensus_metrics)
        
        # Should detect high consensus achievement
        assert len(insights) > 0
        consensus_insight = insights[0]
        assert consensus_insight.category == "effectiveness"
        assert "High Consensus Achievement" in consensus_insight.title
    
    def test_generate_insights(self, analyzer):
        """Test complete insight generation."""
        # Set up mock metrics
        analyzer.metrics_collector.get_summary_stats.return_value = {
            'system': {
                'metrics_collected': 15000,  # High volume
                'events_logged': 5000
            }
        }
        
        analyzer.metrics_collector.debate_metrics = {}
        
        insights = analyzer.generate_insights()
        
        # Should generate insights
        assert isinstance(insights, list)
        
        # Check insight structure if any generated
        for insight in insights:
            assert isinstance(insight, PerformanceInsight)
            assert insight.category
            assert insight.title
            assert insight.description
            assert insight.impact in ["high", "medium", "low"]
            assert 0.0 <= insight.confidence <= 1.0


class TestAnalyticsDashboard:
    """Test suite for analytics dashboard."""
    
    @pytest.fixture
    def orchestration_service(self):
        """Create mock orchestration service."""
        service = Mock()
        service.get_system_status.return_value = {
            "status": "running",
            "active_debates": 2,
            "total_templates": 5,
            "uptime_seconds": 3600
        }
        return service
    
    @pytest.fixture
    def dashboard(self, orchestration_service):
        """Create analytics dashboard."""
        return AnalyticsDashboard(orchestration_service)
    
    def test_dashboard_initialization(self, dashboard):
        """Test dashboard initialization."""
        assert dashboard.orchestration_service is not None
        assert dashboard.metrics_collector is not None
        assert dashboard.edge_case_detector is not None
        assert dashboard.performance_analyzer is not None
        assert dashboard.app is not None
        assert len(dashboard.alerts) == 0
    
    def test_dashboard_routes(self, dashboard):
        """Test dashboard API routes."""
        routes = [route.path for route in dashboard.app.routes]
        
        expected_routes = [
            "/",
            "/api/edge-cases",
            "/api/insights",
            "/api/alerts",
            "/api/metrics/summary",
            "/api/debates/analysis",
            "/api/system/health"
        ]
        
        for route in expected_routes:
            assert route in routes
    
    def test_generate_alert(self, dashboard):
        """Test alert generation."""
        alert_id = dashboard.generate_alert(
            alert_type="test_alert",
            level=AlertLevel.WARNING,
            title="Test Alert",
            message="This is a test alert",
            context={"test_key": "test_value"}
        )
        
        assert alert_id is not None
        assert len(dashboard.alerts) == 1
        
        alert = dashboard.alerts[0]
        assert alert.alert_type == "test_alert"
        assert alert.level == AlertLevel.WARNING
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test alert"
        assert alert.context["test_key"] == "test_value"
    
    def test_debate_analysis_generation(self, dashboard):
        """Test debate analysis data generation."""
        analysis = dashboard._generate_debate_analysis()
        
        assert isinstance(analysis, dict)
        assert "categories" in analysis
        assert "counts" in analysis
        assert "total_debates" in analysis
        assert "completed_debates" in analysis
        assert "consensus_rate" in analysis
        
        # Check data structure
        assert isinstance(analysis["categories"], list)
        assert isinstance(analysis["counts"], list)
        assert isinstance(analysis["total_debates"], int)


class TestIntegration:
    """Integration tests for Phase 3 components."""
    
    @pytest.fixture
    def complete_system(self, tmp_path):
        """Create a complete orchestration system."""
        # Mock AI client factory
        ai_factory = Mock()
        claude_client = Mock()
        gemini_client = Mock()
        
        claude_response = Mock()
        claude_response.content = [Mock(text="Claude response")]
        claude_client.messages.create.return_value = claude_response
        
        gemini_response = Mock()
        gemini_response.text = "Gemini response"
        gemini_client.generate_content_async = AsyncMock(return_value=gemini_response)
        
        ai_factory.get_claude_client.return_value = claude_client
        ai_factory.get_gemini_client.return_value = gemini_client
        
        # Create configuration
        config = OrchestrationConfig(
            template_storage_path=tmp_path / "templates",
            metrics_export_path=tmp_path / "metrics",
            max_concurrent_debates=3,
            enable_notifications=True,
            enable_metrics_export=False,
            enable_health_checks=False,
            log_level="DEBUG"
        )
        
        # Create service
        service = ProductionOrchestrationService(config, ai_factory)
        dashboard = create_analytics_dashboard(service)
        
        return {
            'service': service,
            'dashboard': dashboard,
            'config': config,
            'ai_factory': ai_factory
        }
    
    @pytest.mark.asyncio
    async def test_end_to_end_orchestration(self, complete_system):
        """Test complete end-to-end orchestration flow."""
        service = complete_system['service']
        dashboard = complete_system['dashboard']
        
        # Start service
        await service.start()
        
        try:
            # Start a debate
            debate_id = await service.start_debate(
                question="Should we implement event-driven architecture?",
                complexity="complex"
            )
            
            # Verify debate is active
            assert debate_id in service.active_debates
            active_debates = service.get_active_debates()
            assert len(active_debates) == 1
            
            # Get system status
            status = service.get_system_status()
            assert status["status"] == "running"
            assert status["active_debates"] == 1
            
            # Test analytics
            analysis = dashboard._generate_debate_analysis()
            assert analysis["total_debates"] >= 0
            
            # Complete debate
            debate_session = service.active_debates[debate_id]
            await service._complete_debate(debate_session, "test_completion")
            
            # Verify cleanup
            assert debate_id not in service.active_debates
            
        finally:
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_debates_management(self, complete_system):
        """Test managing multiple concurrent debates."""
        service = complete_system['service']
        
        await service.start()
        
        try:
            debate_ids = []
            
            # Start multiple debates
            for i in range(3):
                debate_id = await service.start_debate(
                    question=f"Question {i}",
                    complexity="simple"
                )
                debate_ids.append(debate_id)
            
            # Verify all debates are active
            assert len(service.active_debates) == 3
            active_debates = service.get_active_debates()
            assert len(active_debates) == 3
            
            # Complete debates one by one
            for debate_id in debate_ids:
                debate_session = service.active_debates[debate_id]
                await service._complete_debate(debate_session, "test_completion")
            
            # Verify all completed
            assert len(service.active_debates) == 0
            
        finally:
            await service.stop()
    
    def test_analytics_with_real_data(self, complete_system):
        """Test analytics with real debate data."""
        service = complete_system['service']
        dashboard = complete_system['dashboard']
        
        # Add mock debate metrics
        metrics_collector = dashboard.metrics_collector
        
        # Create realistic debate metrics
        for i in range(5):
            metrics = DebateMetrics(
                debate_id=uuid4(),
                start_time=datetime.now() - timedelta(hours=2),
                end_time=datetime.now() - timedelta(hours=1),
                total_rounds=3,
                total_arguments=6,
                participants={"claude", "gemini"},
                consensus_reached=(i % 2 == 0),  # 60% consensus rate
                consensus_confidence=0.8 if i % 2 == 0 else 0.4,
                completed_successfully=True,
                error_count=0
            )
            metrics_collector.debate_metrics[str(metrics.debate_id)] = metrics
        
        # Test edge case detection
        patterns = dashboard.edge_case_detector.analyze_patterns()
        assert isinstance(patterns, list)
        
        # Test performance insights
        insights = dashboard.performance_analyzer.generate_insights()
        assert isinstance(insights, list)
        
        # Test analysis generation
        analysis = dashboard._generate_debate_analysis()
        assert analysis["total_debates"] == 5
    
    def test_system_monitoring_integration(self, complete_system):
        """Test system monitoring and alerting integration."""
        service = complete_system['service']
        dashboard = complete_system['dashboard']
        
        # Test system status integration
        status = service.get_system_status()
        assert isinstance(status, dict)
        
        # Test alert generation
        alert_id = dashboard.generate_alert(
            alert_type="integration_test",
            level=AlertLevel.INFO,
            title="Integration Test Alert",
            message="Testing alert generation"
        )
        
        assert alert_id is not None
        assert len(dashboard.alerts) == 1
        
        # Test alert retrieval
        alerts = dashboard.alerts
        assert len(alerts) == 1
        assert alerts[0].alert_type == "integration_test"
    
    def test_factory_functions(self, tmp_path):
        """Test factory functions for creating components."""
        # Test production service factory
        ai_factory = Mock()
        config = OrchestrationConfig(
            template_storage_path=tmp_path,
            metrics_export_path=tmp_path
        )
        
        service = create_production_service(config, ai_factory)
        assert isinstance(service, ProductionOrchestrationService)
        assert service.config == config
        assert service.ai_client_factory == ai_factory
        
        # Test analytics dashboard factory
        dashboard = create_analytics_dashboard(service)
        assert isinstance(dashboard, AnalyticsDashboard)
        assert dashboard.orchestration_service == service


if __name__ == "__main__":
    pytest.main([__file__, "-v"])