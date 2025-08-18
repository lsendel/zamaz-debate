#!/usr/bin/env python3
"""
Test script for Evolution Quality Management API endpoints
Validates the new web API functionality
"""

import asyncio
import json
from src.core.nucleus import DebateNucleus

async def test_evolution_quality_api():
    """Test the evolution quality management through DebateNucleus"""
    
    print("🧪 Testing Evolution Quality Management API")
    print("=" * 50)
    
    # Initialize nucleus
    nucleus = DebateNucleus()
    
    # Test 1: Add a test evolution with proper type classification
    print("\n1️⃣ Testing Evolution Addition with Type Classification")
    test_evolution = {
        "type": "enhancement", 
        "feature": "api_improvement",
        "description": "Improve API response times and enhance error handling for better user experience"
    }
    
    success = nucleus.evolution_tracker.add_evolution(test_evolution)
    print(f"Evolution added: {success}")
    
    # Test 2: Generate quality report
    print("\n2️⃣ Testing Quality Report Generation")
    try:
        report = nucleus.evolution_tracker.get_evolution_quality_report()
        if isinstance(report, dict) and "total_evolutions" in report:
            print(f"✅ Quality report generated successfully")
            print(f"   Total evolutions: {report.get('total_evolutions', 0)}")
            print(f"   Quality score: {report.get('quality_score', 0)}")
            print(f"   Recommendations: {len(report.get('recommendations', []))}")
        else:
            print(f"❌ Invalid quality report format")
            return False
    except Exception as e:
        print(f"❌ Error generating quality report: {e}")
        return False
    
    # Test 3: Get recommendations
    print("\n3️⃣ Testing Evolution Recommendations")
    try:
        recommendations = nucleus.evolution_tracker.get_evolution_recommendations()
        print(f"✅ Recommendations generated: {len(recommendations)} items")
        for i, rec in enumerate(recommendations[:3], 1):  # Show first 3
            print(f"   {i}. {rec.get('recommendation', 'N/A')}")
    except Exception as e:
        print(f"❌ Error getting recommendations: {e}")
        return False
    
    # Test 4: Test evolution success tracking
    print("\n4️⃣ Testing Evolution Success Tracking")
    evolutions = nucleus.evolution_tracker.get_active_evolutions()
    if evolutions:
        latest_evolution = evolutions[-1]
        evolution_id = latest_evolution['id']
        
        success_metrics = {
            "implementation_completed": True,
            "tests_passing": True,
            "performance_improved": 0.85,
            "no_regressions": True
        }
        
        tracking_success = nucleus.evolution_tracker.track_evolution_success(evolution_id, success_metrics)
        print(f"✅ Success tracking: {tracking_success}")
        
        # Verify the evolution was updated
        updated_evolutions = nucleus.evolution_tracker.get_active_evolutions()
        updated_evolution = next((e for e in updated_evolutions if e['id'] == evolution_id), None)
        if updated_evolution and 'success_score' in updated_evolution:
            print(f"   Success score: {updated_evolution['success_score']}")
            print(f"   Status: {updated_evolution.get('status', 'unknown')}")
        else:
            print(f"❌ Evolution not properly updated")
            return False
    else:
        print("❌ No evolutions found for testing")
        return False
    
    # Test 5: Test type classification accuracy with real examples
    print("\n5️⃣ Testing Type Classification with Real Examples")
    test_cases = [
        ("The system needs better security", "Add authentication and encryption", "security"),
        ("Fix the memory leak in the worker process", "Resolve resource cleanup issue", "fix"),
        ("We should optimize the database queries", "Make queries faster and more efficient", "performance"),
        ("Implement a new user dashboard feature", "Add analytics dashboard for users", "feature")
    ]
    
    correct = 0
    for claude, gemini, expected in test_cases:
        result = nucleus.evolution_tracker._extract_evolution_type(claude, gemini)
        if result == expected:
            correct += 1
            print(f"   ✅ '{expected}' classified correctly")
        else:
            print(f"   ❌ Expected '{expected}', got '{result}'")
    
    accuracy = correct / len(test_cases)
    print(f"   📊 Classification accuracy: {accuracy:.1%}")
    
    return accuracy >= 0.75  # Expect at least 75% accuracy

async def main():
    """Run the API tests"""
    print("🚀 Evolution Quality Management System - API Test Suite")
    print("=" * 60)
    
    success = await test_evolution_quality_api()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All API tests passed! Evolution Quality Management System is working.")
    else:
        print("⚠️  Some API tests failed. Check the implementation.")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)