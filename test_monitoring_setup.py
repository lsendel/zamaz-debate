#!/usr/bin/env python3
"""
Test script to validate monitoring setup components
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_monitoring_imports():
    """Test that all monitoring modules can be imported"""
    try:
        from src.infrastructure.monitoring.config import MonitoringConfig
        print("✓ Successfully imported MonitoringConfig")
        
        from src.infrastructure.monitoring.grafana_dashboards import GrafanaDashboardGenerator
        print("✓ Successfully imported GrafanaDashboardGenerator")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_config_loading():
    """Test configuration loading from environment"""
    try:
        from src.infrastructure.monitoring.config import MonitoringConfig
        config = MonitoringConfig.from_env()
        
        print("✓ Configuration loaded successfully")
        print(f"  - Prometheus enabled: {config.prometheus.enabled}")
        print(f"  - Prometheus port: {config.prometheus.port}")
        print(f"  - Grafana enabled: {config.grafana.enabled}")
        print(f"  - Grafana port: {config.grafana.port}")
        print(f"  - Alerting enabled: {config.alerting.enabled}")
        
        return config
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return None

def test_dashboard_generation(config):
    """Test dashboard generation"""
    try:
        from src.infrastructure.monitoring.grafana_dashboards import GrafanaDashboardGenerator
        
        generator = GrafanaDashboardGenerator(config)
        
        # Test generating each dashboard
        dashboards = {
            "main": generator.generate_main_dashboard(),
            "kafka": generator.generate_kafka_dashboard(),
            "performance": generator.generate_performance_dashboard(),
            "debug": generator.generate_debug_dashboard(),
        }
        
        print(f"✓ Generated {len(dashboards)} dashboards")
        
        # Validate dashboard structure
        for name, dashboard in dashboards.items():
            if "dashboard" in dashboard:
                print(f"  - {name}: {dashboard['dashboard']['title']}")
            else:
                print(f"  - {name}: Missing dashboard structure")
        
        return dashboards
    except Exception as e:
        print(f"✗ Dashboard generation error: {e}")
        return None

def test_directory_creation():
    """Test that required directories can be created"""
    try:
        monitoring_dir = Path("monitoring")
        test_dirs = [
            monitoring_dir / "grafana" / "dashboards",
            monitoring_dir / "prometheus",
            monitoring_dir / "alertmanager",
        ]
        
        for directory in test_dirs:
            if directory.exists():
                print(f"✓ Directory exists: {directory}")
            else:
                print(f"- Directory needs to be created: {directory}")
        
        return True
    except Exception as e:
        print(f"✗ Directory check error: {e}")
        return False

def main():
    """Run all monitoring setup tests"""
    print("🎯 Testing Monitoring Setup Components")
    print("=" * 50)
    
    # Test 1: Import modules
    print("\n📦 Testing module imports...")
    if not test_monitoring_imports():
        print("❌ Module import test failed")
        return False
    
    # Test 2: Load configuration
    print("\n⚙️  Testing configuration loading...")
    config = test_config_loading()
    if not config:
        print("❌ Configuration test failed")
        return False
    
    # Test 3: Generate dashboards
    print("\n📊 Testing dashboard generation...")
    dashboards = test_dashboard_generation(config)
    if not dashboards:
        print("❌ Dashboard generation test failed")
        return False
    
    # Test 4: Check directories
    print("\n📁 Testing directory structure...")
    if not test_directory_creation():
        print("❌ Directory structure test failed")
        return False
    
    print("\n✅ All monitoring setup tests passed!")
    print("\nNext steps:")
    print("1. Run the actual setup script: python scripts/setup_monitoring.py")
    print("2. Check generated files in monitoring/ directory")
    print("3. Start monitoring stack: cd monitoring && docker-compose up -d")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)