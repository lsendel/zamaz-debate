#!/usr/bin/env python3
"""
Monitoring Setup Script

Sets up comprehensive monitoring for the Zamaz Debate System including:
- Generates Grafana dashboard configurations
- Creates Docker Compose setup for Prometheus/Grafana
- Provides setup instructions and validation
"""

import os
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.infrastructure.monitoring.grafana_dashboards import GrafanaDashboardGenerator
from src.infrastructure.monitoring.config import MonitoringConfig


class MonitoringSetup:
    """Setup and configuration manager for monitoring infrastructure"""
    
    def __init__(self, project_root: Path = None):
        """Initialize setup manager"""
        self.project_root = project_root or Path(__file__).parent.parent
        self.monitoring_dir = self.project_root / "monitoring"
        self.config = MonitoringConfig.from_env()
        
    def setup_directories(self):
        """Create necessary directories for monitoring"""
        directories = [
            self.monitoring_dir,
            self.monitoring_dir / "prometheus",
            self.monitoring_dir / "grafana" / "provisioning" / "datasources",
            self.monitoring_dir / "grafana" / "provisioning" / "dashboards", 
            self.monitoring_dir / "grafana" / "dashboards",
            self.monitoring_dir / "alertmanager",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created directory: {directory}")
    
    def generate_grafana_dashboards(self):
        """Generate Grafana dashboard JSON files"""
        generator = GrafanaDashboardGenerator(self.config)
        
        dashboards = {
            "zamaz-overview.json": generator.generate_main_dashboard(),
            "zamaz-kafka.json": generator.generate_kafka_dashboard(),
            "zamaz-performance.json": generator.generate_performance_dashboard(),
            "zamaz-debug.json": generator.generate_debug_dashboard(),
        }
        
        dashboard_dir = self.monitoring_dir / "grafana" / "dashboards"
        
        for filename, dashboard_config in dashboards.items():
            filepath = dashboard_dir / filename
            with open(filepath, 'w') as f:
                json.dump(dashboard_config, f, indent=2)
            print(f"✓ Generated dashboard: {filename}")
        
        print(f"✓ Generated {len(dashboards)} Grafana dashboards")
    
    def create_environment_file(self):
        """Create .env file with monitoring configuration"""
        env_file = self.project_root / ".env.monitoring"
        
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
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print(f"✓ Created monitoring environment file: {env_file}")
        print("  Add these variables to your main .env file or source this file")
    
    def validate_setup(self):
        """Validate monitoring setup"""
        print("\n🔍 Validating monitoring setup...")
        
        # Check required directories
        required_dirs = [
            self.monitoring_dir / "prometheus",
            self.monitoring_dir / "grafana" / "dashboards",
            self.monitoring_dir / "alertmanager",
        ]
        
        for directory in required_dirs:
            if directory.exists():
                print(f"✓ Directory exists: {directory}")
            else:
                print(f"✗ Missing directory: {directory}")
        
        # Check required files
        required_files = [
            self.monitoring_dir / "docker-compose.yml",
            self.monitoring_dir / "prometheus" / "prometheus.yml",
            self.monitoring_dir / "alertmanager" / "alertmanager.yml",
        ]
        
        for filepath in required_files:
            if filepath.exists():
                print(f"✓ File exists: {filepath}")
            else:
                print(f"✗ Missing file: {filepath}")
        
        # Check dashboard files
        dashboard_dir = self.monitoring_dir / "grafana" / "dashboards"
        dashboard_files = list(dashboard_dir.glob("*.json"))
        if dashboard_files:
            print(f"✓ Found {len(dashboard_files)} dashboard files")
        else:
            print("✗ No dashboard files found")
    
    def check_dependencies(self):
        """Check for required dependencies"""
        print("\n📦 Checking dependencies...")
        
        # Check for Docker
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ Docker: {result.stdout.strip()}")
            else:
                print("✗ Docker not found")
        except FileNotFoundError:
            print("✗ Docker not found")
        
        # Check for Docker Compose
        try:
            result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ Docker Compose: {result.stdout.strip()}")
            else:
                print("✗ Docker Compose not found")
        except FileNotFoundError:
            print("✗ Docker Compose not found")
        
        # Check for Python dependencies
        try:
            import prometheus_client
            print("✓ prometheus_client library available")
        except ImportError:
            print("✗ prometheus_client library not found")
            print("  Install with: pip install prometheus_client")
        
        try:
            import psutil
            print("✓ psutil library available")
        except ImportError:
            print("✗ psutil library not found") 
            print("  Install with: pip install psutil")
    
    def generate_setup_instructions(self):
        """Generate setup instructions"""
        instructions = f"""
# 🚀 Zamaz Debate System Monitoring Setup

## Prerequisites
- Docker and Docker Compose installed
- Python packages: prometheus_client, psutil

## Setup Steps

### 1. Install Python Dependencies
```bash
pip install prometheus_client psutil
```

### 2. Configure Environment
Copy the monitoring environment variables to your .env file:
```bash
cat .env.monitoring >> .env
```

### 3. Start Monitoring Stack
```bash
cd {self.monitoring_dir}
docker-compose up -d
```

### 4. Update Web Application
Add monitoring integration to your FastAPI app in `src/web/app.py`:

```python
from src.infrastructure.monitoring.web_integration import MonitoringIntegration

# Initialize monitoring
monitoring = MonitoringIntegration()

# Add monitoring router
app.include_router(monitoring.router)

# Add monitoring middleware (optional)
# app.add_middleware(monitoring.middleware)

# Update startup event
@app.on_event("startup")
async def startup_event():
    # ... existing startup code ...
    await monitoring.start()

# Update shutdown event  
@app.on_event("shutdown")
async def shutdown_event():
    # ... existing shutdown code ...
    await monitoring.stop()
```

### 5. Access Monitoring Services

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Alertmanager**: http://localhost:9093
- **Application Metrics**: http://localhost:8090/metrics
- **Health Checks**: http://localhost:8000/monitoring/health

### 6. Import Grafana Dashboards

Dashboards are automatically provisioned, or import manually:

1. Open Grafana (http://localhost:3000)
2. Login with admin/admin
3. Navigate to "+" → Import
4. Upload dashboard JSON files from `{self.monitoring_dir}/grafana/dashboards/`

## Dashboard Overview

### Main Overview Dashboard
- System health status
- Uptime and resource usage
- Kafka event flow rates
- Debate activity and duration

### Kafka Monitoring Dashboard  
- Connection status and active consumers
- Event production/consumption rates by context
- Consumer lag monitoring
- Producer/consumer performance

### Performance Dashboard
- CPU, memory, disk, and network usage
- HTTP response times and throughput
- Error rates and benchmarks
- Optimization tracking

### Debug Dashboard
- Event bus internals
- Component health checks
- System debugging information

## Alerting

Alerts are configured for:
- System resource thresholds
- Kafka connectivity issues
- Consumer lag warnings
- Performance degradation
- Component health failures

## Troubleshooting

### Metrics Not Appearing
1. Check that the web application is running with monitoring enabled
2. Verify Prometheus can reach the metrics endpoint: http://localhost:8090/metrics
3. Check Prometheus targets: http://localhost:9090/targets

### Grafana Dashboards Empty
1. Verify Prometheus is configured as data source
2. Check that metrics are being collected
3. Verify dashboard queries match metric names

### Docker Issues
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs prometheus
docker-compose logs grafana
docker-compose logs alertmanager

# Restart services
docker-compose restart
```

## Configuration

Edit configuration files in `{self.monitoring_dir}/`:
- `prometheus/prometheus.yml` - Prometheus scraping configuration
- `prometheus/alert_rules.yml` - Alerting rules
- `alertmanager/alertmanager.yml` - Alert routing and notifications
- `grafana/provisioning/` - Grafana provisioning configuration

## Scaling

For production deployments:
1. Use external Prometheus/Grafana instances
2. Configure persistent storage volumes
3. Set up alert notification channels (Slack, email, etc.)
4. Enable Grafana authentication and user management
5. Configure SSL/TLS for all services
"""
        
        readme_file = self.monitoring_dir / "README.md"
        with open(readme_file, 'w') as f:
            f.write(instructions)
        
        print(f"✓ Generated setup instructions: {readme_file}")
    
    def run_setup(self):
        """Run complete monitoring setup"""
        print("🎯 Setting up Zamaz Debate System Monitoring")
        print("=" * 50)
        
        # Check dependencies first
        self.check_dependencies()
        
        # Create directories
        print("\n📁 Setting up directories...")
        self.setup_directories()
        
        # Generate dashboard files
        print("\n📊 Generating Grafana dashboards...")
        self.generate_grafana_dashboards()
        
        # Create environment file
        print("\n⚙️  Creating environment configuration...")
        self.create_environment_file()
        
        # Generate setup instructions
        print("\n📝 Generating setup instructions...")
        self.generate_setup_instructions()
        
        # Validate setup
        self.validate_setup()
        
        print("\n✅ Monitoring setup complete!")
        print(f"\nNext steps:")
        print(f"1. Review generated files in {self.monitoring_dir}")
        print(f"2. Add environment variables from .env.monitoring to your .env file")
        print(f"3. Start monitoring stack: cd {self.monitoring_dir} && docker-compose up -d")
        print(f"4. Integrate monitoring into your web app (see README.md)")
        print(f"\nFor detailed instructions, see: {self.monitoring_dir}/README.md")


def main():
    """Main setup function"""
    setup = MonitoringSetup()
    setup.run_setup()


if __name__ == "__main__":
    main()