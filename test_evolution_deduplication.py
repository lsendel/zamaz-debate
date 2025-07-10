#!/usr/bin/env python3
"""
Test script for Enhanced Evolution Deduplication
This script validates the improved deduplication mechanisms in the EvolutionTracker
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.evolution_tracker import EvolutionTracker


def test_enhanced_deduplication():
    """Test enhanced deduplication mechanisms"""
    print("🧪 Testing Enhanced Evolution Deduplication")
    print("=" * 50)
    
    # Create a temporary tracker for testing
    test_dir = Path(__file__).parent / "test_data" / "evolutions"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    tracker = EvolutionTracker(str(test_dir))
    
    # Clear existing data for clean test
    tracker.history = {
        "evolutions": [],
        "fingerprints": set(),
        "created_at": datetime.now().isoformat()
    }
    
    print("1. Testing Basic Fingerprinting Enhancement")
    print("-" * 30)
    
    # Test 1: Basic evolution should be added
    evolution1 = {
        "type": "feature",
        "feature": "performance_optimization",
        "description": "Implement advanced performance monitoring with real-time metrics tracking and alerting system",
        "decision_text": "Based on analysis, we need comprehensive performance monitoring"
    }
    
    result1 = tracker.add_evolution(evolution1)
    print(f"✓ First evolution added: {result1}")
    assert result1 == True, "First evolution should be added"
    
    # Test 2: Exact duplicate should be rejected
    evolution2 = evolution1.copy()
    result2 = tracker.add_evolution(evolution2)
    print(f"✓ Exact duplicate rejected: {not result2}")
    assert result2 == False, "Exact duplicate should be rejected"
    
    print("\n2. Testing Time-Based Deduplication")
    print("-" * 30)
    
    # Test 3: Similar evolution within time window should be rejected
    evolution3 = {
        "type": "feature",
        "feature": "performance_optimization",
        "description": "Add performance monitoring system with metrics collection",
        "decision_text": "We should implement performance tracking capabilities"
    }
    
    result3 = tracker.add_evolution(evolution3)
    print(f"✓ Similar evolution within time window rejected: {not result3}")
    assert result3 == False, "Similar evolution within time window should be rejected"
    
    print("\n3. Testing Semantic Similarity Detection")
    print("-" * 30)
    
    # Test 4: Semantically similar evolution should be rejected
    evolution4 = {
        "type": "feature",
        "feature": "performance_optimization",
        "description": "Create performance tracking system with monitoring and alerting",
        "decision_text": "Implementation of performance monitoring infrastructure"
    }
    
    result4 = tracker.add_evolution(evolution4)
    print(f"✓ Semantically similar evolution rejected: {not result4}")
    assert result4 == False, "Semantically similar evolution should be rejected"
    
    print("\n4. Testing Different Feature Types")
    print("-" * 30)
    
    # Test 5: Different feature should be allowed
    evolution5 = {
        "type": "feature",
        "feature": "security_enhancement",
        "description": "Implement OAuth2 authentication with JWT tokens",
        "decision_text": "Security improvements are needed for API endpoints"
    }
    
    result5 = tracker.add_evolution(evolution5)
    print(f"✓ Different feature type accepted: {result5}")
    assert result5 == True, "Different feature type should be accepted"
    
    print("\n5. Testing Enhanced Fingerprinting")
    print("-" * 30)
    
    # Test 6: Similar generic feature with different specific content
    evolution6 = {
        "type": "feature",
        "feature": "general_improvement",
        "description": "Implement Docker containerization with Kubernetes deployment",
        "decision_text": "Containerization will improve deployment consistency"
    }
    
    evolution7 = {
        "type": "feature",
        "feature": "general_improvement",
        "description": "Add Redis caching layer for database optimization",
        "decision_text": "Caching will improve application performance"
    }
    
    result6 = tracker.add_evolution(evolution6)
    result7 = tracker.add_evolution(evolution7)
    print(f"✓ Generic feature with Docker content: {result6}")
    print(f"✓ Generic feature with Redis content: {result7}")
    assert result6 == True, "Generic feature with specific Docker content should be accepted"
    assert result7 == True, "Generic feature with specific Redis content should be accepted"
    
    print("\n6. Testing Duplicate Analysis")
    print("-" * 30)
    
    # Add some test duplicates to analyze
    test_time = datetime.now() - timedelta(minutes=30)
    
    # Manually add some duplicates to test analysis
    duplicate_evolution = {
        "id": "test_duplicate_1",
        "type": "feature",
        "feature": "performance_optimization",
        "description": "Performance monitoring system implementation",
        "timestamp": test_time.isoformat(),
        "fingerprint": "test_fingerprint_1"
    }
    
    tracker.history["evolutions"].append(duplicate_evolution)
    
    duplicate_evolution2 = {
        "id": "test_duplicate_2",
        "type": "feature",
        "feature": "performance_optimization",
        "description": "Performance monitoring system implementation",
        "timestamp": (test_time + timedelta(minutes=10)).isoformat(),
        "fingerprint": "test_fingerprint_2"
    }
    
    tracker.history["evolutions"].append(duplicate_evolution2)
    
    analysis = tracker.analyze_duplicates()
    print(f"✓ Duplicate analysis found {analysis['duplicate_pairs']} duplicate pairs")
    print(f"✓ Total evolutions analyzed: {analysis['total_evolutions']}")
    print(f"✓ Most duplicated features: {analysis['most_duplicated_features'][:3]}")
    
    print("\n7. Testing Unique Evolution Suggestions")
    print("-" * 30)
    
    # Test unique evolution suggestion
    mock_debate_results = {
        "claude": "We should implement performance optimization with caching",
        "gemini": "Performance improvements through caching would be beneficial",
        "final_decision": "Implement performance caching system",
        "id": "test_debate_123"
    }
    
    unique_suggestion = tracker.suggest_unique_evolution(mock_debate_results)
    if unique_suggestion:
        print(f"✓ Unique evolution suggested: {unique_suggestion['feature']}")
    else:
        print("✓ No unique evolution suggested (all variations are duplicates)")
    
    print("\n8. Final Statistics")
    print("-" * 30)
    
    summary = tracker.get_evolution_summary()
    print(f"✓ Total evolutions: {summary['total_evolutions']}")
    print(f"✓ Evolution types: {summary['evolution_types']}")
    
    # Test fingerprint generation improvements
    print("\n9. Testing Fingerprint Generation")
    print("-" * 30)
    
    # Test that different generic features get different fingerprints
    generic1 = {
        "type": "feature",
        "feature": "performance_optimization",
        "description": "Implement Kafka message queuing system",
        "decision_text": "Kafka will improve message processing"
    }
    
    generic2 = {
        "type": "feature",
        "feature": "performance_optimization",
        "description": "Add PostgreSQL database optimization",
        "decision_text": "Database performance needs improvement"
    }
    
    fp1 = tracker._generate_fingerprint(generic1)
    fp2 = tracker._generate_fingerprint(generic2)
    
    print(f"✓ Kafka fingerprint: {fp1[:16]}...")
    print(f"✓ PostgreSQL fingerprint: {fp2[:16]}...")
    print(f"✓ Fingerprints are different: {fp1 != fp2}")
    assert fp1 != fp2, "Different specific content should generate different fingerprints"
    
    print("\n" + "=" * 50)
    print("🎉 All Enhanced Deduplication Tests Passed!")
    print("=" * 50)
    
    return True


def test_real_world_scenario():
    """Test with real-world duplicate scenarios"""
    print("\n🌍 Testing Real-World Duplicate Scenarios")
    print("=" * 50)
    
    # Create a fresh tracker
    test_dir = Path(__file__).parent / "test_data" / "evolutions_real"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    tracker = EvolutionTracker(str(test_dir))
    tracker.history = {
        "evolutions": [],
        "fingerprints": set(),
        "created_at": datetime.now().isoformat()
    }
    
    # Simulate the actual duplicate scenario from the issue
    performance_evolutions = [
        {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Implement performance monitoring and metrics collection",
            "decision_text": "Performance tracking is needed for system optimization"
        },
        {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Add performance monitoring with real-time metrics",
            "decision_text": "Real-time performance tracking will help identify bottlenecks"
        },
        {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Create performance optimization framework",
            "decision_text": "Framework for performance improvements across the system"
        },
        {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Implement performance profiling and analysis",
            "decision_text": "Profiling tools will help identify performance issues"
        },
        {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Add performance monitoring dashboard",
            "decision_text": "Dashboard for visualizing performance metrics"
        }
    ]
    
    print("Adding 5 similar performance optimization evolutions...")
    results = []
    for i, evolution in enumerate(performance_evolutions):
        result = tracker.add_evolution(evolution)
        results.append(result)
        print(f"Evolution {i+1}: {'✓ Added' if result else '✗ Rejected as duplicate'}")
    
    print(f"\nResults: {sum(results)} accepted, {len(results) - sum(results)} rejected")
    print(f"✓ Duplicate prevention working: {len(results) - sum(results) > 0}")
    
    # Test the analysis on this scenario
    analysis = tracker.analyze_duplicates()
    print(f"\nDuplicate Analysis Results:")
    print(f"- Total evolutions: {analysis['total_evolutions']}")
    print(f"- Duplicate pairs found: {analysis['duplicate_pairs']}")
    print(f"- Feature distribution: {analysis['feature_counts']}")
    
    return True


if __name__ == "__main__":
    try:
        test_enhanced_deduplication()
        test_real_world_scenario()
        print("\n🎯 All tests completed successfully!")
        print("The enhanced deduplication system is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)