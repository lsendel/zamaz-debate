"""
Grafana Dashboard Configurations

Pre-configured Grafana dashboards for the Zamaz Debate System monitoring.
Includes dashboards for Kafka events, performance metrics, debates, and system health.
"""

import json
from typing import Dict, Any, List
from .config import MonitoringConfig


class GrafanaDashboardGenerator:
    """Generates Grafana dashboard configurations"""
    
    def __init__(self, config: MonitoringConfig):
        """Initialize with monitoring configuration"""
        self.config = config
        self.prometheus_prefix = {
            "kafka": config.prometheus.kafka_prefix,
            "performance": config.prometheus.performance_prefix,
            "debate": config.prometheus.debate_prefix,
            "system": config.prometheus.system_prefix,
        }
    
    def generate_main_dashboard(self) -> Dict[str, Any]:
        """Generate the main overview dashboard"""
        return {
            "dashboard": {
                "id": None,
                "title": "Zamaz Debate System - Overview",
                "description": "Main overview dashboard for the Zamaz Debate System",
                "tags": ["zamaz", "overview"],
                "timezone": "browser",
                "refresh": self.config.grafana.refresh_interval,
                "time": {
                    "from": f"now-{self.config.grafana.time_range}",
                    "to": "now"
                },
                "panels": [
                    # System health row
                    self._create_row_panel("System Health", 0),
                    self._create_stat_panel(
                        "System Status", 
                        f'{self.prometheus_prefix["system"]}_health_check_status{{component="event_bus"}}',
                        1, 0, 6, 3,
                        thresholds=[
                            {"color": "red", "value": 0},
                            {"color": "green", "value": 1}
                        ],
                        mappings=[
                            {"type": "value", "value": "0", "text": "Unhealthy"},
                            {"type": "value", "value": "1", "text": "Healthy"}
                        ]
                    ),
                    self._create_stat_panel(
                        "Uptime",
                        f'{self.prometheus_prefix["system"]}_uptime_seconds',
                        2, 6, 6, 3,
                        unit="s"
                    ),
                    self._create_gauge_panel(
                        "CPU Usage",
                        f'{self.prometheus_prefix["performance"]}_cpu_usage_percent',
                        3, 12, 6, 3,
                        max_value=100,
                        unit="percent"
                    ),
                    self._create_gauge_panel(
                        "Memory Usage",
                        f'{self.prometheus_prefix["performance"]}_memory_usage_percent',
                        4, 18, 6, 3,
                        max_value=100,
                        unit="percent"
                    ),
                    
                    # Kafka events row
                    self._create_row_panel("Kafka Events", 5),
                    self._create_time_series_panel(
                        "Event Production Rate",
                        f'rate({self.prometheus_prefix["kafka"]}_events_produced_total[5m])',
                        6, 0, 12, 6,
                        legend="{{context}}"
                    ),
                    self._create_time_series_panel(
                        "Event Consumption Rate", 
                        f'rate({self.prometheus_prefix["kafka"]}_events_consumed_total[5m])',
                        7, 12, 12, 6,
                        legend="{{context}}"
                    ),
                    self._create_stat_panel(
                        "Active Consumers",
                        f'{self.prometheus_prefix["kafka"]}_active_consumers',
                        8, 0, 6, 3
                    ),
                    self._create_stat_panel(
                        "Bridged Event Types",
                        f'{self.prometheus_prefix["kafka"]}_bridged_event_types',
                        9, 6, 6, 3
                    ),
                    
                    # Debates row
                    self._create_row_panel("Debates & Decisions", 10),
                    self._create_time_series_panel(
                        "Debates Started",
                        f'rate({self.prometheus_prefix["debate"]}_debates_started_total[5m])',
                        11, 0, 8, 6,
                        legend="{{complexity}}"
                    ),
                    self._create_time_series_panel(
                        "Debate Duration",
                        f'{self.prometheus_prefix["debate"]}_debate_duration_seconds',
                        12, 8, 8, 6,
                        legend="{{complexity}}"
                    ),
                    self._create_stat_panel(
                        "Tasks Created Today",
                        f'increase({self.prometheus_prefix["debate"]}_tasks_created_total[24h])',
                        13, 16, 8, 6
                    ),
                ]
            }
        }
    
    def generate_kafka_dashboard(self) -> Dict[str, Any]:
        """Generate detailed Kafka monitoring dashboard"""
        return {
            "dashboard": {
                "id": None,
                "title": "Zamaz Debate System - Kafka Monitoring",
                "description": "Detailed Kafka event monitoring dashboard",
                "tags": ["zamaz", "kafka", "events"],
                "timezone": "browser", 
                "refresh": self.config.grafana.refresh_interval,
                "time": {
                    "from": f"now-{self.config.grafana.time_range}",
                    "to": "now"
                },
                "panels": [
                    # Connection status
                    self._create_row_panel("Kafka Connection", 0),
                    self._create_stat_panel(
                        "Connection Status",
                        f'{self.prometheus_prefix["kafka"]}_connection_status',
                        1, 0, 8, 3,
                        thresholds=[
                            {"color": "red", "value": 0},
                            {"color": "green", "value": 1}
                        ],
                        mappings=[
                            {"type": "value", "value": "0", "text": "Disconnected"},
                            {"type": "value", "value": "1", "text": "Connected"}
                        ]
                    ),
                    self._create_stat_panel(
                        "Active Consumers",
                        f'{self.prometheus_prefix["kafka"]}_active_consumers',
                        2, 8, 8, 3
                    ),
                    self._create_stat_panel(
                        "Bridged Event Types",
                        f'{self.prometheus_prefix["kafka"]}_bridged_event_types',
                        3, 16, 8, 3
                    ),
                    
                    # Event flow
                    self._create_row_panel("Event Flow", 4),
                    self._create_time_series_panel(
                        "Events Produced by Context",
                        f'rate({self.prometheus_prefix["kafka"]}_events_produced_total[1m])',
                        5, 0, 12, 8,
                        legend="{{context}} - {{topic}}"
                    ),
                    self._create_time_series_panel(
                        "Events Consumed by Context", 
                        f'rate({self.prometheus_prefix["kafka"]}_events_consumed_total[1m])',
                        6, 12, 12, 8,
                        legend="{{context}} - {{topic}}"
                    ),
                    
                    # Consumer lag
                    self._create_row_panel("Consumer Performance", 7),
                    self._create_time_series_panel(
                        "Consumer Lag",
                        f'{self.prometheus_prefix["kafka"]}_consumer_lag',
                        8, 0, 24, 6,
                        legend="{{context}} - Partition {{partition}}"
                    ),
                    self._create_time_series_panel(
                        "Producer Send Rate",
                        f'{self.prometheus_prefix["kafka"]}_producer_send_rate',
                        9, 0, 12, 6,
                        legend="{{context}}"
                    ),
                    self._create_time_series_panel(
                        "Consumer Consumption Rate",
                        f'{self.prometheus_prefix["kafka"]}_consumer_consumption_rate',
                        10, 12, 12, 6,
                        legend="{{context}}"
                    ),
                ]
            }
        }
    
    def generate_performance_dashboard(self) -> Dict[str, Any]:
        """Generate performance monitoring dashboard"""
        return {
            "dashboard": {
                "id": None,
                "title": "Zamaz Debate System - Performance",
                "description": "System performance and resource monitoring",
                "tags": ["zamaz", "performance", "resources"],
                "timezone": "browser",
                "refresh": self.config.grafana.refresh_interval,
                "time": {
                    "from": f"now-{self.config.grafana.time_range}",
                    "to": "now"
                },
                "panels": [
                    # System resources
                    self._create_row_panel("System Resources", 0),
                    self._create_time_series_panel(
                        "CPU Usage",
                        f'{self.prometheus_prefix["performance"]}_cpu_usage_percent',
                        1, 0, 12, 6,
                        unit="percent",
                        max_value=100
                    ),
                    self._create_time_series_panel(
                        "Memory Usage",
                        f'{self.prometheus_prefix["performance"]}_memory_usage_percent',
                        2, 12, 12, 6,
                        unit="percent",
                        max_value=100
                    ),
                    self._create_time_series_panel(
                        "Disk I/O",
                        f'rate({self.prometheus_prefix["performance"]}_disk_io_bytes_total[1m])',
                        3, 0, 12, 6,
                        legend="{{operation}}",
                        unit="Bps"
                    ),
                    self._create_time_series_panel(
                        "Network I/O",
                        f'rate({self.prometheus_prefix["performance"]}_network_io_bytes_total[1m])',
                        4, 12, 12, 6,
                        legend="{{direction}}",
                        unit="Bps"
                    ),
                    
                    # Application performance
                    self._create_row_panel("Application Performance", 5),
                    self._create_time_series_panel(
                        "Response Time",
                        f'{self.prometheus_prefix["performance"]}_response_time_seconds',
                        6, 0, 12, 6,
                        legend="{{endpoint}} {{method}}",
                        unit="s"
                    ),
                    self._create_gauge_panel(
                        "Error Rate",
                        f'{self.prometheus_prefix["performance"]}_error_rate_percent',
                        7, 12, 6, 6,
                        unit="percent",
                        max_value=100,
                        thresholds=[
                            {"color": "green", "value": 0},
                            {"color": "yellow", "value": 1},
                            {"color": "red", "value": 5}
                        ]
                    ),
                    self._create_stat_panel(
                        "Throughput",
                        f'{self.prometheus_prefix["performance"]}_throughput_requests_per_second',
                        8, 18, 6, 6,
                        unit="reqps"
                    ),
                    
                    # Benchmarks
                    self._create_row_panel("Benchmarks", 9),
                    self._create_time_series_panel(
                        "Benchmark Duration",
                        f'{self.prometheus_prefix["performance"]}_benchmark_duration_seconds',
                        10, 0, 24, 6,
                        legend="{{benchmark_name}}",
                        unit="s"
                    ),
                ]
            }
        }
    
    def generate_debug_dashboard(self) -> Dict[str, Any]:
        """Generate debug and system internals dashboard"""
        return {
            "dashboard": {
                "id": None,
                "title": "Zamaz Debate System - Debug",
                "description": "System internals and debugging information",
                "tags": ["zamaz", "debug", "internals"],
                "timezone": "browser",
                "refresh": self.config.grafana.refresh_interval,
                "time": {
                    "from": f"now-{self.config.grafana.time_range}",
                    "to": "now"
                },
                "panels": [
                    # Event bus
                    self._create_row_panel("Event Bus", 0),
                    self._create_stat_panel(
                        "Event Bus Size",
                        f'{self.prometheus_prefix["system"]}_event_bus_size',
                        1, 0, 8, 3
                    ),
                    self._create_stat_panel(
                        "Active Contexts",
                        f'{self.prometheus_prefix["system"]}_active_contexts',
                        2, 8, 8, 3
                    ),
                    
                    # Health checks
                    self._create_row_panel("Health Checks", 3),
                    self._create_table_panel(
                        "Component Health",
                        f'{self.prometheus_prefix["system"]}_health_check_status',
                        4, 0, 24, 8
                    ),
                ]
            }
        }
    
    def _create_row_panel(self, title: str, panel_id: int) -> Dict[str, Any]:
        """Create a row panel for grouping"""
        return {
            "id": panel_id,
            "title": title,
            "type": "row",
            "collapsed": False,
            "gridPos": {"h": 1, "w": 24, "x": 0, "y": panel_id * 7}
        }
    
    def _create_stat_panel(
        self,
        title: str,
        query: str, 
        panel_id: int,
        x: int, y: int, w: int, h: int,
        unit: str = "short",
        thresholds: List[Dict[str, Any]] = None,
        mappings: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a stat panel"""
        panel = {
            "id": panel_id,
            "title": title,
            "type": "stat",
            "targets": [{"expr": query, "refId": "A"}],
            "gridPos": {"h": h, "w": w, "x": x, "y": y},
            "options": {
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                    "fields": ""
                }
            },
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "custom": {"displayMode": "basic"}
                }
            }
        }
        
        if thresholds:
            panel["fieldConfig"]["defaults"]["thresholds"] = {
                "mode": "absolute",
                "steps": thresholds
            }
        
        if mappings:
            panel["fieldConfig"]["defaults"]["mappings"] = mappings
        
        return panel
    
    def _create_gauge_panel(
        self,
        title: str,
        query: str,
        panel_id: int,
        x: int, y: int, w: int, h: int,
        unit: str = "short",
        min_value: float = 0,
        max_value: float = 100,
        thresholds: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a gauge panel"""
        panel = {
            "id": panel_id,
            "title": title,
            "type": "gauge",
            "targets": [{"expr": query, "refId": "A"}],
            "gridPos": {"h": h, "w": w, "x": x, "y": y},
            "options": {
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                    "fields": ""
                }
            },
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "min": min_value,
                    "max": max_value,
                    "custom": {"displayMode": "basic"}
                }
            }
        }
        
        if thresholds:
            panel["fieldConfig"]["defaults"]["thresholds"] = {
                "mode": "absolute",
                "steps": thresholds
            }
        
        return panel
    
    def _create_time_series_panel(
        self,
        title: str,
        query: str,
        panel_id: int, 
        x: int, y: int, w: int, h: int,
        legend: str = "{{__name__}}",
        unit: str = "short",
        max_value: float = None
    ) -> Dict[str, Any]:
        """Create a time series panel"""
        panel = {
            "id": panel_id,
            "title": title,
            "type": "timeseries",
            "targets": [{"expr": query, "refId": "A", "legendFormat": legend}],
            "gridPos": {"h": h, "w": w, "x": x, "y": y},
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "custom": {
                        "drawStyle": "line",
                        "lineInterpolation": "linear",
                        "lineWidth": 1,
                        "fillOpacity": 10,
                        "spanNulls": False
                    }
                }
            },
            "options": {
                "legend": {
                    "calcs": [],
                    "displayMode": "table",
                    "placement": "bottom"
                }
            }
        }
        
        if max_value:
            panel["fieldConfig"]["defaults"]["max"] = max_value
        
        return panel
    
    def _create_table_panel(
        self,
        title: str, 
        query: str,
        panel_id: int,
        x: int, y: int, w: int, h: int
    ) -> Dict[str, Any]:
        """Create a table panel"""
        return {
            "id": panel_id,
            "title": title,
            "type": "table",
            "targets": [{"expr": query, "refId": "A", "format": "table"}],
            "gridPos": {"h": h, "w": w, "x": x, "y": y},
            "options": {
                "showHeader": True
            },
            "fieldConfig": {
                "defaults": {
                    "custom": {
                        "align": "auto",
                        "displayMode": "auto"
                    }
                }
            }
        }
    
    def save_dashboards_to_files(self, output_dir: str = "./monitoring/dashboards") -> None:
        """Save all dashboard configurations to JSON files"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        dashboards = {
            "main-overview.json": self.generate_main_dashboard(),
            "kafka-monitoring.json": self.generate_kafka_dashboard(),
            "performance.json": self.generate_performance_dashboard(),
            "debug.json": self.generate_debug_dashboard(),
        }
        
        for filename, dashboard in dashboards.items():
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(dashboard, f, indent=2)
        
        print(f"Saved {len(dashboards)} dashboard configurations to {output_dir}")