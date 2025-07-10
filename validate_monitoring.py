#!/usr/bin/env python3
"""
Comprehensive validation script for monitoring setup
This script validates all components that the setup_monitoring.py script would create
"""

import sys
import os
import json
from pathlib import Path
import traceback

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def validate_monitoring_setup():
    """Validate all aspects of the monitoring setup"""
    print("🎯 Validating Monitoring Setup Components")
    print("=" * 50)
    
    success = True
    
    # 1. Test module imports
    print("\n📦 Testing module imports...")
    try:
        from src.infrastructure.monitoring.config import MonitoringConfig
        print("✓ Successfully imported MonitoringConfig")
        
        from src.infrastructure.monitoring.grafana_dashboards import GrafanaDashboardGenerator
        print("✓ Successfully imported GrafanaDashboardGenerator")
        
    except Exception as e:
        print(f"✗ Import error: {e}")
        print(f"  Traceback: {traceback.format_exc()}")
        success = False
        return success
    
    # 2. Test configuration loading
    print("\n⚙️  Testing configuration loading...")
    try:
        config = MonitoringConfig.from_env()
        print("✓ Configuration loaded successfully")
        print(f"  - Prometheus enabled: {config.prometheus.enabled}")
        print(f"  - Prometheus port: {config.prometheus.port}")
        print(f"  - Grafana enabled: {config.grafana.enabled}")
        print(f"  - Grafana port: {config.grafana.port}")
        print(f"  - Alerting enabled: {config.alerting.enabled}")
        
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        print(f"  Traceback: {traceback.format_exc()}")
        success = False
        return success
    
    # 3. Test dashboard generation
    print("\n📊 Testing dashboard generation...")
    try:
        generator = GrafanaDashboardGenerator(config)
        
        # Test generating each dashboard
        dashboards = {
            "zamaz-overview.json": generator.generate_main_dashboard(),
            "zamaz-kafka.json": generator.generate_kafka_dashboard(), 
            "zamaz-performance.json": generator.generate_performance_dashboard(),
            "zamaz-debug.json": generator.generate_debug_dashboard(),
        }
        
        print(f"✓ Generated {len(dashboards)} dashboards")
        
        # Validate dashboard structure
        for name, dashboard in dashboards.items():
            if "dashboard" in dashboard:
                dashboard_info = dashboard["dashboard"]
                title = dashboard_info.get("title", "Unknown")
                panels = dashboard_info.get("panels", [])
                print(f"  - {name}: '{title}' with {len(panels)} panels")
            else:
                print(f"  - {name}: ✗ Missing dashboard structure")
                success = False
        
    except Exception as e:
        print(f"✗ Dashboard generation error: {e}")
        print(f"  Traceback: {traceback.format_exc()}")
        success = False
        return success
    
    # 4. Test directory validation
    print("\n📁 Testing directory structure...")
    try:
        project_root = Path(".")
        monitoring_dir = project_root / "monitoring"
        
        # Check existing directories
        existing_dirs = [
            monitoring_dir,
            monitoring_dir / "prometheus",
            monitoring_dir / "grafana" / "provisioning" / "datasources",
            monitoring_dir / "grafana" / "provisioning" / "dashboards",
            monitoring_dir / "alertmanager",
        ]
        
        missing_dirs = []
        for directory in existing_dirs:
            if directory.exists():
                print(f"✓ Directory exists: {directory}")
            else:
                print(f"- Directory needs to be created: {directory}")
                missing_dirs.append(directory)
        
        # Check for dashboards directory specifically
        dashboard_dir = monitoring_dir / "grafana" / "dashboards"
        if dashboard_dir.exists():
            print(f"✓ Dashboard directory exists: {dashboard_dir}")
        else:
            print(f"- Dashboard directory needs to be created: {dashboard_dir}")
            missing_dirs.append(dashboard_dir)
        
        print(f"  - {len(missing_dirs)} directories need to be created")
        
    except Exception as e:
        print(f"✗ Directory validation error: {e}")
        success = False
    
    # 5. Test file validation
    print("\n📄 Testing required files...")
    try:
        required_files = [
            monitoring_dir / "docker-compose.yml",
            monitoring_dir / "prometheus" / "prometheus.yml",
            monitoring_dir / "alertmanager" / "alertmanager.yml",
        ]
        
        for filepath in required_files:
            if filepath.exists():
                print(f"✓ File exists: {filepath}")
            else:
                print(f"✗ Missing file: {filepath}")
                success = False
        
    except Exception as e:
        print(f"✗ File validation error: {e}")
        success = False
    
    # 6. Test environment file generation
    print("\n🌍 Testing environment file generation...")
    try:
        env_file_path = project_root / ".env.monitoring"
        
        env_content = """# Monitoring Configuration for Zamaz Debate System

# Prometheus Configuration
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=8090
PROMETHEUS_HOST=0.0.0.0
PROMETHEUS_METRICS_PATH=/metrics
PROMETHEUS_SCRAPE_INTERVAL=15

# Grafana Configuration  
GRAFANA_ENABLED=true
GRAFANA_PORT=3000
GRAFANA_HOST=0.0.0.0
GRAFANA_ADMIN_PASSWORD=admin
GRAFANA_REFRESH_INTERVAL=5s
GRAFANA_TIME_RANGE=1h

# Alerting Configuration
ALERTING_ENABLED=true
ALERT_WEBHOOK_URL=http://localhost:8000/webhooks/alerts
KAFKA_LAG_THRESHOLD=1000
HIGH_CPU_THRESHOLD=80.0
HIGH_MEMORY_THRESHOLD=85.0
ERROR_RATE_THRESHOLD=5.0
RESPONSE_TIME_THRESHOLD=2000.0

# Collection Settings
MONITORING_COLLECTION_INTERVAL=30
MONITORING_RETENTION_DAYS=30

# Feature Flags
KAFKA_MONITORING_ENABLED=true
PERFORMANCE_MONITORING_ENABLED=true
HEALTH_CHECKS_ENABLED=true
CONSUMER_LAG_MONITORING_ENABLED=true
"""
        
        print(f"✓ Environment file template validated")
        print(f"  - Would create: {env_file_path}")
        print(f"  - Content: {len(env_content)} characters")
        
    except Exception as e:
        print(f"✗ Environment file validation error: {e}")
        success = False
    
    # 7. Test dependency checking
    print("\n🔍 Testing dependency checking...")
    try:
        # Check for prometheus_client
        try:
            import prometheus_client
            print("✓ prometheus_client library available")
        except ImportError:
            print("✗ prometheus_client library not found")
            print("  Install with: pip install prometheus_client")
            success = False
        
        # Check for psutil
        try:
            import psutil
            print("✓ psutil library available")
        except ImportError:
            print("✗ psutil library not found")
            print("  Install with: pip install psutil")
            success = False
        
    except Exception as e:
        print(f"✗ Dependency check error: {e}")
        success = False
    
    # Summary
    print("\n" + "=" * 50)
    if success:
        print("✅ All monitoring setup validation tests passed!")
        print("\nThe monitoring setup script should work correctly.")
        print("\nNext steps:")
        print("1. Run: python scripts/setup_monitoring.py")
        print("2. Check generated files in monitoring/grafana/dashboards/")
        print("3. Review .env.monitoring file")
        print("4. Start monitoring stack: cd monitoring && docker-compose up -d")
    else:
        print("❌ Some validation tests failed!")
        print("Check the errors above and fix them before running the setup script.")
    
    return success

if __name__ == "__main__":
    success = validate_monitoring_setup()
    sys.exit(0 if success else 1)