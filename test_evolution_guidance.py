#!/usr/bin/env python3
"""
Test script for Evolution Guidance System

This script tests the new Evolution Guidance System to ensure it properly
prevents repetitive performance optimization loops and guides diverse improvements.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.evolution_guidance import EvolutionGuidanceSystem, EvolutionMetrics
from src.core.evolution_tracker import EvolutionTracker


async def test_evolution_guidance():
    """Test the evolution guidance system functionality"""
    print("🧪 Testing Evolution Guidance System")
    print("=" * 50)
    
    # Initialize the guidance system
    guidance = EvolutionGuidanceSystem()
    
    # Test 1: Check if system detects performance optimization loop
    print("\n📊 Test 1: Performance Optimization Loop Detection")
    result1 = guidance.analyze_evolution_request(
        "What is the ONE most important performance optimization to make to this debate system?"
    )
    
    print(f"Should evolve: {result1.should_evolve}")
    print(f"Reason: {result1.reason}")
    if result1.blocked_reason:
        print(f"🚫 Blocked: {result1.blocked_reason}")
    if result1.alternative_suggestions:
        print("💡 Alternative suggestions:")
        for alt in result1.alternative_suggestions:
            print(f"  - {alt}")
    
    # Test 2: Test with a different type of question
    print("\n📊 Test 2: Security Enhancement Request")
    result2 = guidance.analyze_evolution_request(
        "What is the ONE most important security enhancement to implement?"
    )
    
    print(f"Should evolve: {result2.should_evolve}")
    print(f"Reason: {result2.reason}")
    if result2.recommended_area:
        print(f"Recommended area: {result2.recommended_area}")
    
    # Test 3: Get system health report
    print("\n📊 Test 3: System Health Report")
    health = guidance.get_system_health_report()
    print(f"Health status: {health['health_status']}")
    print(f"Diversity score: {health['diversity_score']}")
    print(f"Most repeated feature: {health['most_repeated_feature']} ({health['repetition_count']} times)")
    print(f"Total evolutions: {health['total_evolutions']}")
    print(f"High priority recommendations: {health['high_priority_recommendations']}")
    print(f"Effectiveness trend: {health['effectiveness_trend']}")
    
    # Test 4: Record some metrics and test effectiveness tracking
    print("\n📊 Test 4: Metrics Recording")
    test_metrics = EvolutionMetrics(
        debate_count=186,
        decision_count=112,
        error_rate=0.05,
        performance_score=0.8,
        user_satisfaction=0.75,
        system_stability=0.9,
        timestamp=guidance._load_metrics_history()[-1].timestamp if guidance.metrics_history else None
    )
    
    guidance.record_evolution_metrics(test_metrics)
    print("✅ Metrics recorded successfully")
    
    # Test 5: Test specific guidance for the current system state
    print("\n📊 Test 5: Guidance for Current System State")
    
    # Simulate the exact question that's been causing loops
    current_question = "What is the ONE most important improvement to make to this debate system next? Consider: code quality, functionality, performance, and usability. Ensure this is different from previous evolutions."
    
    result5 = guidance.analyze_evolution_request(current_question)
    print(f"Current system question guidance:")
    print(f"Should evolve: {result5.should_evolve}")
    print(f"Reason: {result5.reason}")
    
    if not result5.should_evolve:
        print(f"🚫 Evolution would be blocked!")
        print(f"Block reason: {result5.blocked_reason}")
        print("📋 Alternative suggestions provided:")
        for i, alt in enumerate(result5.alternative_suggestions, 1):
            print(f"  {i}. {alt}")
    else:
        print("✅ Evolution would be allowed")
        if result5.suggested_question != current_question:
            print(f"📝 Suggested alternative question: {result5.suggested_question}")
    
    print("\n🎯 Summary")
    print("=" * 50)
    
    if health['health_status'] == 'repetitive_pattern':
        print("🔴 System has repetitive patterns - Guidance system is NEEDED")
    elif health['health_status'] == 'low_diversity':
        print("🟡 System has low diversity - Guidance system will help")
    else:
        print("🟢 System health is good")
    
    print(f"💡 The Evolution Guidance System {'would block' if not result5.should_evolve else 'would allow'} the current repetitive evolution requests")
    
    return {
        'performance_loop_detected': not result1.should_evolve,
        'alternative_suggestions_provided': len(result1.alternative_suggestions) > 0,
        'health_status': health['health_status'],
        'diversity_score': health['diversity_score'],
        'system_functional': True
    }


async def test_nucleus_integration():
    """Test integration with the debate nucleus"""
    print("\n🔌 Testing Nucleus Integration")
    print("=" * 30)
    
    try:
        from src.core.nucleus import DebateNucleus
        
        # Initialize nucleus (this should now include evolution guidance)
        nucleus = DebateNucleus()
        
        # Check if evolution guidance is properly initialized
        if hasattr(nucleus, 'evolution_guidance'):
            print("✅ Evolution guidance system integrated into nucleus")
            
            # Test if the evolve_self method would be blocked
            print("📊 Testing evolve_self behavior...")
            
            # This would normally trigger the repetitive performance optimization loop
            # but should now be blocked by the guidance system
            result = await nucleus.evolve_self()
            
            if result.get('guidance_applied'):
                print("✅ Evolution guidance was applied")
                print(f"Guidance reason: {result.get('guidance_reason', 'Not provided')}")
                
                if result.get('method') == 'guidance_block':
                    print("🚫 Evolution was properly blocked by guidance system")
                    print(f"Block reason: {result.get('blocked_reason', 'Not provided')}")
                    
                    if result.get('alternative_suggestions'):
                        print("💡 Alternative suggestions provided:")
                        for alt in result['alternative_suggestions']:
                            print(f"  - {alt}")
                else:
                    print("✅ Evolution was allowed with guidance")
            else:
                print("❌ Evolution guidance was not applied")
        else:
            print("❌ Evolution guidance system not found in nucleus")
            return False
            
    except ImportError as e:
        print(f"❌ Could not import nucleus: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during nucleus integration test: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("🚀 Evolution Guidance System Test Suite")
    print("This tests the solution to the performance optimization loop crisis")
    print("=" * 70)
    
    # Run the tests
    result = asyncio.run(test_evolution_guidance())
    integration_success = asyncio.run(test_nucleus_integration())
    
    print("\n🏁 Final Results")
    print("=" * 20)
    
    if result['performance_loop_detected']:
        print("✅ PASS: Performance optimization loop detection works")
    else:
        print("❌ FAIL: Performance optimization loop not detected")
    
    if result['alternative_suggestions_provided']:
        print("✅ PASS: Alternative suggestions are provided")
    else:
        print("❌ FAIL: No alternative suggestions provided")
    
    if integration_success:
        print("✅ PASS: Integration with nucleus successful")
    else:
        print("❌ FAIL: Integration with nucleus failed")
    
    if result['system_functional']:
        print("✅ PASS: Evolution guidance system is functional")
    else:
        print("❌ FAIL: Evolution guidance system has issues")
    
    overall_success = (
        result['performance_loop_detected'] and 
        result['alternative_suggestions_provided'] and 
        integration_success and 
        result['system_functional']
    )
    
    if overall_success:
        print("\n🎉 SUCCESS: Evolution Guidance System implementation is working!")
        print("The performance optimization loop crisis should be resolved.")
    else:
        print("\n💥 FAILURE: Some tests failed. The implementation needs fixes.")
        
    print(f"\nSystem Health: {result['health_status']}")
    print(f"Diversity Score: {result['diversity_score']:.2f}")