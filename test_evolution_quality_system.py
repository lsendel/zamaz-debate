#!/usr/bin/env python3
"""
Test script for Evolution Quality Management System
Validates the enhanced evolution tracker improvements
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.core.evolution_tracker import EvolutionTracker
import json

def test_evolution_type_classification():
    """Test the improved evolution type classification"""
    tracker = EvolutionTracker()
    
    test_cases = [
        # Test case: (claude_text, gemini_text, expected_type)
        ("We should improve the performance of the system", "Make it faster and more efficient", "enhancement"),
        ("Add a new caching system to the application", "Implement Redis caching for better performance", "feature"),
        ("Fix the bug causing crashes when users login", "Resolve the authentication error", "fix"),
        ("Refactor the code to make it more maintainable", "Clean up technical debt and simplify", "refactor"),
        ("The system needs better security and authentication", "Harden the security with proper encryption", "security"),
        ("Add unit tests to improve test coverage", "Implement automated testing framework", "testing"),
        ("Update the documentation to be clearer", "Write better API docs and guides", "documentation"),
        ("Optimize the database queries for speed", "Improve query performance and reduce latency", "performance"),
    ]
    
    print("🧪 Testing Evolution Type Classification")
    print("=" * 50)
    
    correct = 0
    for i, (claude, gemini, expected) in enumerate(test_cases, 1):
        result = tracker._extract_evolution_type(claude, gemini)
        status = "✅" if result == expected else "❌"
        print(f"{status} Test {i}: Expected '{expected}', Got '{result}'")
        print(f"   Claude: {claude[:50]}...")
        print(f"   Gemini: {gemini[:50]}...")
        print()
        if result == expected:
            correct += 1
    
    accuracy = correct / len(test_cases)
    print(f"📊 Accuracy: {correct}/{len(test_cases)} ({accuracy:.1%})")
    return accuracy > 0.7  # Expect at least 70% accuracy

def test_duplicate_detection():
    """Test enhanced duplicate detection"""
    tracker = EvolutionTracker()
    
    print("\n🔍 Testing Duplicate Detection")
    print("=" * 50)
    
    # Add first evolution
    evolution1 = {
        "type": "performance",
        "feature": "performance_optimization",
        "description": "Improve system performance through better algorithms and caching"
    }
    
    # Add similar evolution (should be detected as duplicate)
    evolution2 = {
        "type": "enhancement", 
        "feature": "performance_enhancement",
        "description": "Enhance performance with optimization and better caching strategies"
    }
    
    # Add different evolution (should not be duplicate)
    evolution3 = {
        "type": "testing",
        "feature": "testing_framework",
        "description": "Add comprehensive unit and integration testing suite"
    }
    
    success1 = tracker.add_evolution(evolution1)
    success2 = tracker.add_evolution(evolution2)  # Should be blocked as duplicate
    success3 = tracker.add_evolution(evolution3)  # Should succeed
    
    print(f"✅ First evolution added: {success1}")
    print(f"❌ Duplicate evolution blocked: {not success2}")
    print(f"✅ Different evolution added: {success3}")
    
    return success1 and not success2 and success3

def test_quality_metrics():
    """Test evolution quality tracking"""
    tracker = EvolutionTracker()
    
    print("\n📈 Testing Quality Metrics")
    print("=" * 50)
    
    # Add a test evolution
    evolution = {
        "type": "enhancement",
        "feature": "api_enhancement", 
        "description": "Improve API response times and add better error handling"
    }
    
    success = tracker.add_evolution(evolution)
    if not success:
        print("❌ Failed to add test evolution")
        return False
    
    # Get the evolution ID
    evolutions = tracker.get_active_evolutions()
    if not evolutions:
        print("❌ No evolutions found")
        return False
    
    evolution_id = evolutions[-1]['id']
    
    # Track success metrics
    success_metrics = {
        "implementation_completed": True,
        "tests_passing": True,
        "performance_improved": 0.8,  # 80% improvement
        "no_regressions": True,
        "user_feedback_positive": True,
        "documentation_updated": True
    }
    
    tracking_success = tracker.track_evolution_success(evolution_id, success_metrics)
    print(f"✅ Success tracking: {tracking_success}")
    
    # Generate quality report
    report = tracker.get_evolution_quality_report()
    print(f"📊 Quality report generated: {report is not None}")
    
    if report and 'quality_score' in report:
        print(f"📈 Overall quality score: {report['quality_score']}")
        print(f"📋 Recommendations: {len(report.get('recommendations', []))}")
    
    return tracking_success and report is not None

def run_comprehensive_test():
    """Run all tests and provide summary"""
    print("🚀 Evolution Quality Management System - Test Suite")
    print("=" * 60)
    
    test_results = []
    
    # Run individual tests
    test_results.append(("Type Classification", test_evolution_type_classification()))
    test_results.append(("Duplicate Detection", test_duplicate_detection()))
    test_results.append(("Quality Metrics", test_quality_metrics()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    overall_success = passed == len(test_results)
    print(f"\n🎯 Overall Result: {passed}/{len(test_results)} tests passed")
    
    if overall_success:
        print("🎉 All tests passed! Evolution Quality Management System is working correctly.")
    else:
        print("⚠️  Some tests failed. Review the implementation.")
    
    return overall_success

if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)