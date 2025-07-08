#!/usr/bin/env python3
"""
Deploy the hardened Zamaz Debate System
This script enables the hardened system alongside the existing one
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
import json
from datetime import datetime


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n→ {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"✗ Failed: {result.stderr}")
            return False
        print(f"✓ Success")
        if result.stdout:
            print(f"  Output: {result.stdout.strip()}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    print("🔒 Deploying Hardened Zamaz Debate System")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("src/core/nucleus.py").exists():
        print("✗ Error: Must run from project root directory")
        sys.exit(1)
    
    # Step 1: Create deployment tracking
    deploy_dir = Path("deployment")
    deploy_dir.mkdir(exist_ok=True)
    
    deployment_info = {
        "timestamp": datetime.now().isoformat(),
        "version": "hardened-1.0.0",
        "status": "in_progress"
    }
    
    with open(deploy_dir / "deployment.json", "w") as f:
        json.dump(deployment_info, f, indent=2)
    
    # Step 2: Ensure dependencies are installed
    print("\n📦 Checking dependencies...")
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        print("✗ Failed to install dependencies")
        return False
    
    # Step 3: Create startup scripts
    print("\n📝 Creating startup scripts...")
    
    # Original app startup
    original_startup = """#!/bin/bash
echo "Starting original Zamaz Debate System on port 8000..."
cd "$(dirname "$0")/.."
python -m uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload
"""
    
    # Hardened app startup
    hardened_startup = """#!/bin/bash
echo "Starting hardened Zamaz Debate System on port 8001..."
cd "$(dirname "$0")/.."
python -m uvicorn src.web.app_hardened:app --host 0.0.0.0 --port 8001 --reload
"""
    
    scripts_dir = Path("scripts")
    scripts_dir.mkdir(exist_ok=True)
    
    with open(scripts_dir / "start_original.sh", "w") as f:
        f.write(original_startup)
    
    with open(scripts_dir / "start_hardened.sh", "w") as f:
        f.write(hardened_startup)
    
    # Make scripts executable
    run_command("chmod +x scripts/*.sh", "Making scripts executable")
    
    # Step 4: Create comparison script
    comparison_script = """#!/usr/bin/env python3
'''Compare original and hardened systems'''
import requests
import json
from datetime import datetime

def test_endpoint(url, endpoint, data=None):
    '''Test an endpoint and return results'''
    try:
        if data:
            response = requests.post(f"{url}{endpoint}", json=data, timeout=10)
        else:
            response = requests.get(f"{url}{endpoint}", timeout=10)
        
        return {
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds(),
            "data": response.json() if response.ok else response.text
        }
    except Exception as e:
        return {
            "error": str(e)
        }

def main():
    original_url = "http://localhost:8000"
    hardened_url = "http://localhost:8001"
    
    print("🔍 Comparing Original vs Hardened Systems")
    print("=" * 50)
    
    # Test health endpoints
    print("\\n📋 Health Check:")
    original_health = test_endpoint(original_url, "/health")
    hardened_health = test_endpoint(hardened_url, "/health")
    
    print(f"Original: {original_health.get('status_code', 'Failed')}")
    print(f"Hardened: {hardened_health.get('status_code', 'Failed')} - {hardened_health.get('data', {}).get('status', 'Unknown')}")
    
    # Test stats
    print("\\n📊 Stats:")
    original_stats = test_endpoint(original_url, "/stats")
    hardened_stats = test_endpoint(hardened_url, "/stats")
    
    print(f"Original: {original_stats.get('data', {})}")
    print(f"Hardened: {hardened_stats.get('data', {})}")
    
    # Test decision endpoint
    print("\\n🤔 Decision Test:")
    test_decision = {
        "question": "Should we implement automated testing for all new features?",
        "context": "We want to improve code quality"
    }
    
    original_decision = test_endpoint(original_url, "/decide", test_decision)
    hardened_decision = test_endpoint(hardened_url, "/decide", test_decision)
    
    print(f"Original response time: {original_decision.get('response_time', 'N/A')}s")
    print(f"Hardened response time: {hardened_decision.get('response_time', 'N/A')}s")
    
    # Test rate limiting (hardened only)
    print("\\n🚦 Rate Limiting Test (Hardened):")
    for i in range(12):
        result = test_endpoint(hardened_url, "/stats")
        if result.get('status_code') == 429:
            print(f"  Rate limit hit after {i} requests ✓")
            break
    else:
        print("  Rate limit not triggered (may need adjustment)")
    
    print("\\n✅ Comparison complete!")

if __name__ == "__main__":
    main()
"""
    
    with open(scripts_dir / "compare_systems.py", "w") as f:
        f.write(comparison_script)
    
    run_command("chmod +x scripts/compare_systems.py", "Making comparison script executable")
    
    # Step 5: Create integration plan
    integration_plan = """# Hardened System Integration Plan

## Overview
The hardened system has been deployed alongside the original system to allow for gradual migration and testing.

## Architecture
- **Original System**: Running on port 8000 (src/web/app.py)
- **Hardened System**: Running on port 8001 (src/web/app_hardened.py)

## New Features in Hardened System
1. **Security Enhancements**
   - Input validation and sanitization
   - Rate limiting (10 requests/minute)
   - CORS configuration
   - Command injection prevention

2. **Error Handling**
   - Global exception handlers
   - Retry logic with exponential backoff
   - Circuit breaker pattern
   - Structured error responses

3. **Data Validation**
   - Pydantic models for all inputs/outputs
   - Strict type checking
   - Field validation with patterns

4. **Monitoring**
   - Health check endpoint
   - Structured logging
   - Request tracking

5. **Atomic Operations**
   - File operations with rollback
   - Backup creation
   - Lock protection

## Migration Steps

### Phase 1: Testing (Current)
1. Run both systems in parallel
2. Compare responses and performance
3. Monitor for errors and edge cases

### Phase 2: Gradual Migration
1. Update frontend to use hardened endpoints
2. Redirect traffic gradually (10% → 50% → 100%)
3. Monitor metrics and error rates

### Phase 3: Full Migration
1. Update all internal references
2. Deprecate original endpoints
3. Remove original system code

## Testing Commands

```bash
# Start original system
./scripts/start_original.sh

# Start hardened system (in new terminal)
./scripts/start_hardened.sh

# Run comparison tests (in new terminal)
./scripts/compare_systems.py
```

## Rollback Plan
If issues arise:
1. Stop hardened system
2. All traffic automatically falls back to original
3. Investigate and fix issues
4. Re-deploy hardened system

## Monitoring
- Check logs: `tail -f logs/hardened_*.log`
- Health check: `curl http://localhost:8001/health`
- Rate limit test: Run multiple requests rapidly

## Next Steps
1. Run comprehensive tests
2. Update CI/CD pipeline
3. Create performance benchmarks
4. Document API changes
"""
    
    with open(deploy_dir / "INTEGRATION_PLAN.md", "w") as f:
        f.write(integration_plan)
    
    # Step 6: Update deployment status
    deployment_info["status"] = "completed"
    deployment_info["endpoints"] = {
        "original": "http://localhost:8000",
        "hardened": "http://localhost:8001"
    }
    
    with open(deploy_dir / "deployment.json", "w") as f:
        json.dump(deployment_info, f, indent=2)
    
    print("\n✅ Deployment Complete!")
    print("\n📋 Next Steps:")
    print("1. Start original system: ./scripts/start_original.sh")
    print("2. Start hardened system: ./scripts/start_hardened.sh")
    print("3. Run comparison: ./scripts/compare_systems.py")
    print("4. Read integration plan: deployment/INTEGRATION_PLAN.md")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)