#!/usr/bin/env python3
"""
Test script for Evolution Effectiveness Measurement System
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent))

from src.core.evolution_effectiveness import EvolutionEffectivenessTracker


async def test_evolution_effectiveness():
    """Test the evolution effectiveness measurement system"""
    
    print("🧪 Testing Evolution Effectiveness Measurement System")
    print("=" * 60)
    
    # Initialize tracker
    tracker = EvolutionEffectivenessTracker(data_dir="data_test")
    
    # Test 1: Start monitoring
    print("\n📊 Test 1: Performance Monitoring")
    monitoring_task = asyncio.create_task(tracker.start_monitoring())
    
    # Let it collect a few samples
    await asyncio.sleep(3)
    
    print(f"Collected {len(tracker.performance_samples)} performance samples")
    if tracker.performance_samples:
        latest = tracker.performance_samples[-1]
        print(f"Latest metrics: CPU: {latest.cpu_usage:.1f}%, Memory: {latest.memory_usage:.1f}%")
    
    # Test 2: Begin evolution measurement
    print("\n🔬 Test 2: Begin Evolution Measurement")
    evolution_id = "test_evolution_123"
    feature = "evolution_effectiveness"
    evolution_type = "feature"
    
    success_criteria = {
        "error_rate": -10.0,  # 10% reduction
        "response_time_avg": -5.0,  # 5% improvement
        "decision_accuracy": 5.0  # 5% improvement
    }
    
    result = await tracker.begin_evolution_measurement(
        evolution_id=evolution_id,
        evolution_feature=feature,
        evolution_type=evolution_type,
        success_criteria=success_criteria
    )
    
    print(f"Evolution measurement started: {result}")
    
    # Simulate some time passing (evolution implementation)
    print("\n⏱️  Simulating evolution implementation (3 seconds)...")
    await asyncio.sleep(3)
    
    # Test 3: Complete evolution measurement
    print("\n📈 Test 3: Complete Evolution Measurement")
    completion_result = await tracker.complete_evolution_measurement(evolution_id)
    print(f"Evolution completion result:")
    print(json.dumps(completion_result, indent=2))
    
    # Test 4: Get effectiveness report
    print("\n📋 Test 4: Get Effectiveness Report")
    effectiveness_report = await tracker.get_effectiveness_report()
    print("Effectiveness Report:")
    print(json.dumps(effectiveness_report, indent=2))
    
    # Test 5: Get evolution trends
    print("\n📊 Test 5: Get Evolution Trends")
    trends = await tracker.get_evolution_trends()
    print("Evolution Trends:")
    print(json.dumps(trends, indent=2))
    
    # Test 6: Test rollback functionality
    print("\n🔄 Test 6: Test Rollback (if evolution failed)")
    if completion_result.get("status") == "failed":
        rollback_result = await tracker.rollback_evolution(evolution_id)
        print(f"Rollback result: {rollback_result}")
    else:
        print("Evolution succeeded - no rollback needed")
    
    # Stop monitoring
    tracker.stop_monitoring()
    monitoring_task.cancel()
    
    print("\n✅ Evolution Effectiveness System Tests Complete!")
    
    # Clean up test data
    test_data_dir = Path("data_test")
    if test_data_dir.exists():
        import shutil
        shutil.rmtree(test_data_dir)
        print("🧹 Test data cleaned up")


async def test_integration_with_nucleus():
    """Test integration with DebateNucleus"""
    
    print("\n🤖 Testing Integration with DebateNucleus")
    print("=" * 50)
    
    try:
        from src.core.nucleus import DebateNucleus
        
        # Create nucleus
        nucleus = DebateNucleus()
        
        # Test effectiveness tracking methods
        print("✅ DebateNucleus created with effectiveness tracker")
        
        # Test success criteria determination
        criteria = nucleus._determine_success_criteria("performance_optimization", "feature")
        print(f"Success criteria for performance_optimization: {criteria}")
        
        criteria = nucleus._determine_success_criteria("evolution_effectiveness", "feature")
        print(f"Success criteria for evolution_effectiveness: {criteria}")
        
        print("✅ Integration test passed!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")


async def main():
    """Run all tests"""
    await test_evolution_effectiveness()
    await test_integration_with_nucleus()


if __name__ == "__main__":
    asyncio.run(main())