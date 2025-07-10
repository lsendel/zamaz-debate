#!/usr/bin/env python3
"""
Simple test to verify monitoring components work
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_dashboard_generation():
    """Test dashboard generation"""
    print("Testing dashboard generation...")
    
    try:
        # Import the required modules
        from src.infrastructure.monitoring.config import MonitoringConfig
        from src.infrastructure.monitoring.grafana_dashboards import GrafanaDashboardGenerator
        
        print("✓ Modules imported successfully")
        
        # Load configuration
        config = MonitoringConfig.from_env()
        print("✓ Configuration loaded")
        
        # Create generator
        generator = GrafanaDashboardGenerator(config)
        print("✓ Dashboard generator created")
        
        # Generate dashboards
        dashboards = {
            "main": generator.generate_main_dashboard(),
            "kafka": generator.generate_kafka_dashboard(),
            "performance": generator.generate_performance_dashboard(),
            "debug": generator.generate_debug_dashboard(),
        }
        
        print(f"✓ Generated {len(dashboards)} dashboards")
        
        # Validate each dashboard
        for name, dashboard in dashboards.items():
            if "dashboard" in dashboard:
                dashboard_info = dashboard["dashboard"]
                title = dashboard_info.get("title", "Unknown")
                panels = dashboard_info.get("panels", [])
                print(f"  - {name}: '{title}' with {len(panels)} panels")
            else:
                print(f"  - {name}: ERROR - Missing dashboard structure")
                return False
        
        # Try to save one dashboard to test JSON serialization
        test_dashboard = dashboards["main"]
        test_json = json.dumps(test_dashboard, indent=2)
        print(f"✓ JSON serialization test passed ({len(test_json)} characters)")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_dashboard_generation()
    if success:
        print("\n✅ Dashboard generation test passed!")
        print("The monitoring setup script should work correctly.")
    else:
        print("\n❌ Dashboard generation test failed!")
        print("Check the errors above.")
    
    sys.exit(0 if success else 1)