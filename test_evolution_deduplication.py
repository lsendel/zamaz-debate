#!/usr/bin/env python3
"""
Test script for enhanced evolution deduplication system
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.evolution_tracker import EvolutionTracker


def test_enhanced_deduplication():
    """Test the enhanced deduplication mechanisms"""
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize tracker with temp directory
        tracker = EvolutionTracker(temp_dir)
        
        print("🧪 Testing Enhanced Evolution Deduplication System")
        print("=" * 60)
        
        # Test 1: Exact duplicates (should be blocked)
        print("\n1. Testing exact duplicate detection...")
        
        evolution1 = {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Improve system performance through caching and optimization",
            "debate_id": "test_debate_1"
        }
        
        evolution2 = evolution1.copy()  # Exact duplicate
        
        result1 = tracker.add_evolution(evolution1)
        result2 = tracker.add_evolution(evolution2)
        
        print(f"   First evolution added: {result1}")
        print(f"   Duplicate evolution blocked: {not result2}")
        assert result1 is True, "First evolution should be added"
        assert result2 is False, "Duplicate evolution should be blocked"
        
        # Test 2: Time-based duplicates (should be blocked)
        print("\n2. Testing time-based duplicate detection...")
        
        evolution3 = {
            "type": "feature", 
            "feature": "performance_optimization",
            "description": "Different description but same feature within time window",
            "debate_id": "test_debate_2"
        }
        
        result3 = tracker.add_evolution(evolution3)
        print(f"   Time-based duplicate blocked: {not result3}")
        assert result3 is False, "Time-based duplicate should be blocked"
        
        # Test 3: Semantic similarity detection
        print("\n3. Testing semantic similarity detection...")
        
        evolution4 = {
            "type": "feature",
            "feature": "performance_optimization", 
            "description": "Optimize performance through improved caching mechanisms and system tuning",
            "debate_id": "test_debate_3"
        }
        
        result4 = tracker.add_evolution(evolution4)
        print(f"   Semantically similar evolution blocked: {not result4}")
        assert result4 is False, "Semantically similar evolution should be blocked"
        
        # Test 4: Different features should be allowed
        print("\n4. Testing different features are allowed...")
        
        evolution5 = {
            "type": "feature",
            "feature": "security_enhancement",
            "description": "Improve system security through authentication and authorization",
            "debate_id": "test_debate_4"
        }
        
        result5 = tracker.add_evolution(evolution5)
        print(f"   Different feature allowed: {result5}")
        assert result5 is True, "Different feature should be allowed"
        
        # Test 5: Analyze duplicate patterns
        print("\n5. Testing duplicate analysis...")
        
        # Add more test evolutions for analysis
        test_evolutions = [
            {
                "type": "feature",
                "feature": "monitoring_system",
                "description": "Add monitoring and observability features",
                "debate_id": "test_debate_5"
            },
            {
                "type": "feature", 
                "feature": "monitoring_system",
                "description": "Implement monitoring with metrics and alerts",
                "debate_id": "test_debate_6"
            }
        ]
        
        for evo in test_evolutions:
            tracker.add_evolution(evo)
        
        analysis = tracker.analyze_evolution_duplicates()
        print(f"   Total evolutions analyzed: {analysis['total_evolutions']}")
        print(f"   Unique features: {analysis['unique_features']}")
        print(f"   Duplicate groups found: {len(analysis['duplicate_groups'])}")
        
        # Test 6: Enhanced fingerprint generation
        print("\n6. Testing enhanced fingerprint generation...")
        
        fp1 = tracker._generate_fingerprint(evolution1)
        fp2 = tracker._generate_fingerprint(evolution4)
        
        print(f"   Fingerprint 1 length: {len(fp1)} chars")
        print(f"   Fingerprint 2 length: {len(fp2)} chars")
        print(f"   Fingerprints different: {fp1 != fp2}")
        
        assert len(fp1) == 64, "Fingerprint should be 64 characters"
        assert len(fp2) == 64, "Fingerprint should be 64 characters"
        assert fp1 != fp2, "Different evolutions should have different fingerprints"
        
        # Test 7: Suggest evolution with anti-duplicate
        print("\n7. Testing evolution suggestion with anti-duplicate...")
        
        debate_results = {
            "id": "test_debate_7",
            "claude": "We need performance optimization with caching",
            "gemini": "Performance improvements through optimization",
            "final_decision": "Implement performance optimization"
        }
        
        suggestion = tracker.suggest_evolution_with_anti_duplicate(debate_results)
        print(f"   Evolution suggestion created: {suggestion is not None}")
        
        if suggestion:
            print(f"   Suggested feature: {suggestion['feature']}")
            print(f"   Suggestion type: {suggestion['type']}")
        
        print("\n✅ All tests passed! Enhanced deduplication system is working correctly.")
        
        # Print summary
        summary = tracker.get_evolution_summary()
        print(f"\n📊 Test Summary:")
        print(f"   Total evolutions: {summary['total_evolutions']}")
        print(f"   Evolution types: {summary['evolution_types']}")
        
        return True


def test_duplicate_analysis():
    """Test the duplicate analysis functionality"""
    
    print("\n🔍 Testing Duplicate Analysis on Real Data")
    print("=" * 50)
    
    # Use real data directory
    tracker = EvolutionTracker()
    
    # Analyze existing duplicates
    analysis = tracker.analyze_evolution_duplicates()
    
    print(f"Real data analysis:")
    print(f"   Total evolutions: {analysis['total_evolutions']}")
    print(f"   Unique features: {analysis['unique_features']}")
    print(f"   Duplicate groups: {len(analysis['duplicate_groups'])}")
    
    # Show duplicate groups
    for feature, group in analysis['duplicate_groups'].items():
        print(f"\n   Feature '{feature}': {group['count']} evolutions")
        for evo in group['evolutions'][:3]:  # Show first 3
            print(f"     - {evo['id']} at {evo['timestamp']}")
    
    # Show similarity analysis
    if analysis['similarity_analysis']:
        print(f"\n   High similarity pairs found: {len(analysis['similarity_analysis'])}")
        for sim in analysis['similarity_analysis'][:5]:  # Show first 5
            print(f"     - {sim['evo1_id']} vs {sim['evo2_id']}: {sim['similarity']:.1%} similarity")
    
    # Time clustering analysis
    if analysis['time_clustering']:
        print(f"\n   Time clustering analysis:")
        for feature, cluster in analysis['time_clustering'].items():
            if cluster['rapid_duplicates'] > 0:
                print(f"     - {feature}: {cluster['rapid_duplicates']} rapid duplicates")
    
    return analysis


def test_cleanup_plan():
    """Test the cleanup plan functionality"""
    
    print("\n🧹 Testing Cleanup Plan (Dry Run)")
    print("=" * 40)
    
    tracker = EvolutionTracker()
    
    # Generate cleanup plan
    cleanup_plan = tracker.cleanup_duplicate_evolutions(dry_run=True)
    
    print(f"Cleanup plan results:")
    print(f"   Duplicates found: {cleanup_plan['duplicates_found']}")
    print(f"   Evolutions to remove: {len(cleanup_plan['evolutions_to_remove'])}")
    print(f"   Feature groups affected: {len(cleanup_plan['feature_groups_affected'])}")
    
    # Show what would be removed
    if cleanup_plan['evolutions_to_remove']:
        print(f"\n   Evolutions that would be removed:")
        for evo in cleanup_plan['evolutions_to_remove'][:10]:  # Show first 10
            print(f"     - {evo['id']} ({evo['feature']}) - {evo['reason']}")
    
    if cleanup_plan['feature_groups_affected']:
        print(f"\n   Feature groups with duplicates:")
        for feature in cleanup_plan['feature_groups_affected']:
            print(f"     - {feature}")
    
    return cleanup_plan


if __name__ == "__main__":
    try:
        # Run tests
        test_enhanced_deduplication()
        test_duplicate_analysis()
        test_cleanup_plan()
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)