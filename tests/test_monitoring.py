"""
Tests for the monitoring infrastructure

Basic tests to validate the monitoring system components.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from src.infrastructure.monitoring.config import MonitoringConfig, PrometheusConfig
from src.infrastructure.monitoring.prometheus_metrics import PrometheusMetricsExporter
from src.infrastructure.monitoring.health_checker import HealthChecker, HealthStatus
from src.infrastructure.monitoring.collector import MetricsCollector
from src.infrastructure.monitoring.web_integration import MonitoringIntegration


class TestMonitoringConfig:
    """Test monitoring configuration"""
    
    def test_default_config(self):
        """Test default monitoring configuration"""
        config = MonitoringConfig.from_env()
        assert config.prometheus.enabled is True
        assert config.prometheus.port == 8090
        assert config.collection_interval == 30
        assert config.kafka_monitoring is True
        assert config.performance_monitoring is True
    
    def test_prometheus_config(self):
        """Test Prometheus configuration"""
        config = PrometheusConfig.from_env()
        assert config.metrics_path == "/metrics"
        assert config.kafka_prefix == "zamaz_kafka"
        assert config.performance_prefix == "zamaz_performance"


class TestPrometheusMetricsExporter:
    """Test Prometheus metrics exporter"""
    
    def test_init_with_prometheus_unavailable(self):
        """Test initialization when prometheus_client is not available"""
        with patch('src.infrastructure.monitoring.prometheus_metrics.PROMETHEUS_AVAILABLE', False):
            exporter = PrometheusMetricsExporter()
            assert exporter.enabled is False
    
    def test_init_with_prometheus_available(self):
        """Test initialization when prometheus_client is available"""
        with patch('src.infrastructure.monitoring.prometheus_metrics.PROMETHEUS_AVAILABLE', True):
            config = MonitoringConfig.from_env()
            exporter = PrometheusMetricsExporter(config)
            assert exporter.enabled == config.prometheus.enabled
    
    def test_update_kafka_metrics(self):
        """Test updating Kafka metrics"""
        with patch('src.infrastructure.monitoring.prometheus_metrics.PROMETHEUS_AVAILABLE', True):
            exporter = PrometheusMetricsExporter()
            if exporter.enabled:
                kafka_metrics = {
                    "bridged_event_types": 5,
                    "active_consumers": 3,
                    "event_bus_metrics": {"DebateStarted": 10, "TestCompleted": 5}
                }
                # Should not raise exception
                exporter.update_kafka_metrics(kafka_metrics)
    
    def test_record_debate_events(self):
        """Test recording debate events"""
        with patch('src.infrastructure.monitoring.prometheus_metrics.PROMETHEUS_AVAILABLE', True):
            exporter = PrometheusMetricsExporter()
            if exporter.enabled:
                # Should not raise exception
                exporter.record_debate_started("complex")
                exporter.record_debate_completed("complex", "success", 120.5)
    
    def test_get_metrics_format(self):
        """Test metrics format output"""
        with patch('src.infrastructure.monitoring.prometheus_metrics.PROMETHEUS_AVAILABLE', True):
            exporter = PrometheusMetricsExporter()
            if exporter.enabled:
                metrics = exporter.get_metrics()
                assert isinstance(metrics, str)
                # Should contain some basic metrics
                assert "zamaz_" in metrics or len(metrics) == 0  # Empty if no metrics collected yet


class TestHealthChecker:
    """Test health checker"""
    
    def test_init(self):
        """Test health checker initialization"""
        config = MonitoringConfig.from_env()
        checker = HealthChecker(config)
        assert checker.config == config
    
    @pytest.mark.asyncio
    async def test_system_health_check(self):
        """Test system health check"""
        checker = HealthChecker()
        health = await checker.check_system_health()
        
        assert health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert isinstance(health.checks, list)
        assert len(health.checks) > 0
        assert health.uptime_seconds >= 0
    
    @pytest.mark.asyncio
    async def test_health_summary(self):
        """Test health summary"""
        checker = HealthChecker()
        summary = await checker.get_health_summary()
        
        assert "status" in summary
        assert "uptime_seconds" in summary
        assert "component_count" in summary
        assert "healthy_components" in summary
    
    def test_health_to_dict(self):
        """Test health serialization"""
        checker = HealthChecker()
        # Create a mock health object
        from src.infrastructure.monitoring.health_checker import SystemHealth, HealthCheck
        
        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            checks=[
                HealthCheck(
                    component="test",
                    status=HealthStatus.HEALTHY,
                    message="Test component healthy",
                    timestamp=datetime.now()
                )
            ],
            timestamp=datetime.now(),
            uptime_seconds=100.0
        )
        
        health_dict = checker.to_dict(health)
        assert health_dict["status"] == "healthy"
        assert "checks" in health_dict
        assert len(health_dict["checks"]) == 1


class TestMetricsCollector:
    """Test metrics collector"""
    
    def test_init(self):
        """Test metrics collector initialization"""
        config = MonitoringConfig.from_env()
        collector = MetricsCollector(config)
        assert collector.config == config
    
    def test_get_current_metrics(self):
        """Test getting current metrics"""
        collector = MetricsCollector()
        metrics = collector.get_current_metrics()
        
        assert isinstance(metrics, dict)
        assert "system" in metrics
        assert "events" in metrics
        assert "debates" in metrics
        
        # System metrics should have basic fields
        assert "cpu_usage" in metrics["system"]
        assert "memory_usage" in metrics["system"]
        assert "timestamp" in metrics["system"]


class TestMonitoringIntegration:
    """Test monitoring integration"""
    
    def test_init(self):
        """Test monitoring integration initialization"""
        config = MonitoringConfig.from_env()
        integration = MonitoringIntegration(config)
        
        assert integration.config == config
        assert integration.prometheus_exporter is not None
        assert integration.health_checker is not None
        assert integration.router is not None
    
    def test_router_creation(self):
        """Test that router is created with correct endpoints"""
        from src.infrastructure.monitoring.web_integration import create_monitoring_router
        
        router = create_monitoring_router()
        
        # Check that router has the expected prefix
        assert router.prefix == "/monitoring"
        assert "monitoring" in router.tags
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping monitoring"""
        integration = MonitoringIntegration()
        
        # Should not raise exception
        await integration.start()
        await integration.stop()


class TestMonitoringEndpoints:
    """Test monitoring web endpoints"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_logic(self):
        """Test health endpoint logic"""
        from src.infrastructure.monitoring.health_checker import HealthChecker
        
        checker = HealthChecker()
        health = await checker.check_system_health()
        health_dict = checker.to_dict(health)
        
        # Should have required fields
        assert "status" in health_dict
        assert "timestamp" in health_dict
        assert "uptime_seconds" in health_dict
        assert "checks" in health_dict
    
    def test_metrics_endpoint_logic(self):
        """Test metrics endpoint logic"""
        with patch('src.infrastructure.monitoring.prometheus_metrics.PROMETHEUS_AVAILABLE', True):
            exporter = PrometheusMetricsExporter()
            
            if exporter.enabled:
                metrics = exporter.get_metrics()
                assert isinstance(metrics, str)
            else:
                # When disabled, should handle gracefully
                assert not exporter.is_enabled()


# Integration test with mock components
class TestMonitoringIntegrationFull:
    """Test full monitoring integration"""
    
    def test_full_integration_setup(self):
        """Test complete monitoring setup"""
        config = MonitoringConfig.from_env()
        
        # Create all components
        integration = MonitoringIntegration(config)
        
        # Verify all components are created
        assert integration.prometheus_exporter is not None
        assert integration.health_checker is not None
        assert integration.router is not None
        
        # Verify configuration is passed through
        assert integration.config.prometheus.enabled == config.prometheus.enabled
        assert integration.config.kafka_monitoring == config.kafka_monitoring
    
    @pytest.mark.asyncio
    async def test_kafka_integration_mock(self):
        """Test Kafka integration with mock"""
        integration = MonitoringIntegration()
        
        # Mock Kafka bridge
        mock_kafka_bridge = Mock()
        mock_kafka_bridge.get_metrics.return_value = {
            "bridged_event_types": 5,
            "active_consumers": 2,
            "event_bus_metrics": {"DebateStarted": 10}
        }
        
        integration.set_kafka_bridge(mock_kafka_bridge)
        
        # Verify collector is created
        assert integration.metrics_collector is not None
        
        # Test start/stop
        await integration.start()
        await integration.stop()