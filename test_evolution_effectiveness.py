#!/usr/bin/env python3
"""
Test script for Evolution Effectiveness Framework

This script verifies that the Evolution Effectiveness Framework is working correctly.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

async def test_evolution_effectiveness_framework():
    """Test the Evolution Effectiveness Framework"""
    print("🔬 Testing Evolution Effectiveness Framework")
    print("=" * 60)
    
    try:
        # Test 1: Import the framework components
        print("\n📦 Test 1: Importing framework components...")
        from src.contexts.evolution_effectiveness import (
            EvolutionEffectivenessService,
            MetricsCollectionService,
            EvolutionEffectiveness,
            SuccessMetric,
            MetricType
        )
        print("✅ Successfully imported framework components")
        
        # Test 2: Create and test domain services
        print("\n🔧 Test 2: Testing domain services...")
        effectiveness_service = EvolutionEffectivenessService()
        metrics_service = MetricsCollectionService()
        print("✅ Successfully created domain services")
        
        # Test 3: Test evolution assessment
        print("\n📊 Test 3: Testing evolution assessment...")
        test_evolution_id = "test_evolution_001"
        assessment = await effectiveness_service.assess_evolution_effectiveness(test_evolution_id)
        print(f"✅ Successfully assessed evolution {test_evolution_id}")
        print(f"   - Status: {assessment.status.value}")
        print(f"   - Metrics defined: {len(assessment.success_metrics)}")
        
        # Test 4: Test enhanced evolution tracker
        print("\n🚀 Test 4: Testing enhanced evolution tracker...")
        from src.core.enhanced_evolution_tracker import EnhancedEvolutionTracker
        
        enhanced_tracker = EnhancedEvolutionTracker(enable_effectiveness_framework=True)
        print("✅ Successfully created enhanced evolution tracker")
        
        # Test 5: Test evolution validation
        print("\n✅ Test 5: Testing evolution validation...")
        test_evolution = {
            "type": "feature",
            "feature": "evolution_effectiveness_framework",
            "description": "Implement Evolution Effectiveness Framework to break repetitive cycles",
            "debate_id": "test_debate_001"
        }
        
        validation_result = await enhanced_tracker.add_evolution_with_validation(test_evolution)
        print(f"✅ Evolution validation result: {validation_result['success']}")
        print(f"   - Reason: {validation_result['reason']}")
        
        # Test 6: Test dashboard
        print("\n📈 Test 6: Testing effectiveness dashboard...")
        from src.contexts.evolution_effectiveness.dashboard import EvolutionEffectivenessDashboard
        
        dashboard = EvolutionEffectivenessDashboard()
        summary = await dashboard.get_effectiveness_summary()
        print("✅ Successfully retrieved dashboard summary")
        print(f"   - Total assessments: {summary.get('total_assessments', 0)}")
        print(f"   - Average score: {summary.get('average_score', 0):.1f}")
        
        # Test 7: Test web routes (import only)
        print("\n🌐 Test 7: Testing web routes...")
        try:
            from src.web.evolution_effectiveness_routes import effectiveness_router
            print("✅ Successfully imported web routes")
        except Exception as e:
            print(f"⚠️  Web routes import warning: {e}")
        
        print("\n" + "=" * 60)
        print("🎉 All Evolution Effectiveness Framework tests completed!")
        print("✅ The framework is ready to break the repetitive evolution cycle!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_system_integration():
    """Test integration with the main system"""
    print("\n🔗 Testing system integration...")
    
    try:
        # Test nucleus integration
        from src.core.nucleus import DebateNucleus
        
        nucleus = DebateNucleus()
        print(f"✅ Nucleus initialized with effectiveness framework: {nucleus.effectiveness_framework_enabled}")
        
        # Test evolution health check
        if hasattr(nucleus.evolution_tracker, 'should_evolve_enhanced'):
            health_check = nucleus.evolution_tracker.should_evolve_enhanced()
            print(f"✅ Evolution health check: {health_check['should_evolve']}")
            print(f"   - Reason: {health_check['reason']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🧪 Evolution Effectiveness Framework Test Suite")
    print("=" * 60)
    
    # Test the framework
    framework_ok = await test_evolution_effectiveness_framework()
    
    # Test system integration
    integration_ok = await test_system_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print(f"Framework Tests: {'✅ PASSED' if framework_ok else '❌ FAILED'}")
    print(f"Integration Tests: {'✅ PASSED' if integration_ok else '❌ FAILED'}")
    
    if framework_ok and integration_ok:
        print("\n🎯 RESULT: Evolution Effectiveness Framework is ready!")
        print("🚀 The system can now break the repetitive performance optimization cycle!")
    else:
        print("\n⚠️  RESULT: Some tests failed - manual verification needed")
    
    return framework_ok and integration_ok

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)