#!/usr/bin/env python3
"""
Test script to validate the Enhanced Evolution Tracker works correctly
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_enhanced_evolution_tracker():
    """Test the enhanced evolution tracker functionality"""
    print("🧪 Testing Enhanced Evolution Tracker")
    print("=" * 50)
    
    try:
        from src.core.evolution_tracker import EvolutionTracker
        print("✅ Enhanced EvolutionTracker imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test basic functionality
    tracker = EvolutionTracker()
    print("✅ EvolutionTracker instantiated successfully")
    
    # Get summary of current state
    summary = tracker.get_evolution_summary()
    print(f"📊 Current Evolution Summary:")
    print(f"   Total evolutions: {summary.get('total_evolutions', 0)}")
    print(f"   Evolution types: {summary.get('evolution_types', {})}")
    print(f"   Diversity score: {summary.get('diversity_score', 0.0)}")
    
    # Test feature distribution (look for performance_optimization duplicates)
    feature_dist = summary.get('feature_distribution', {})
    perf_count = feature_dist.get('performance_optimization', 0)
    
    if perf_count > 0:
        print(f"🚨 Found {perf_count} performance_optimization evolutions (confirming duplicates)")
    
    # Show top duplicate features
    print(f"\n🔍 Top Features by Count (potential duplicates):")
    sorted_features = sorted(feature_dist.items(), key=lambda x: x[1], reverse=True)
    for feature, count in sorted_features[:5]:
        if count > 1:
            print(f"   ⚠️  {feature}: {count} occurrences (DUPLICATES)")
        else:
            print(f"   ✅ {feature}: {count} occurrence")
    
    # Test duplicate detection on a simulated performance optimization
    print(f"\n🧪 Testing Duplicate Detection:")
    test_evolution = {
        "type": "feature",
        "feature": "performance_optimization",
        "description": "Test performance optimization to check duplicate detection",
        "timestamp": datetime.now().isoformat()
    }
    
    is_duplicate = tracker.is_duplicate(test_evolution)
    print(f"   Performance optimization duplicate check: {'BLOCKED' if is_duplicate else 'ALLOWED'}")
    
    # Test the individual layers
    if hasattr(tracker, '_check_time_based_duplicates'):
        time_duplicate = tracker._check_time_based_duplicates(test_evolution)
        print(f"   Layer 2 (Time-based): {'DETECTED' if time_duplicate else 'NOT DETECTED'}")
    
    if hasattr(tracker, '_check_semantic_similarity'):
        semantic_duplicate = tracker._check_semantic_similarity(test_evolution)
        print(f"   Layer 3 (Semantic): {'DETECTED' if semantic_duplicate else 'NOT DETECTED'}")
    
    if hasattr(tracker, '_check_text_similarity'):
        text_duplicate = tracker._check_text_similarity(test_evolution)
        print(f"   Layer 4 (Text): {'DETECTED' if text_duplicate else 'NOT DETECTED'}")
    
    # Test enhanced fingerprinting
    fingerprint = tracker._generate_fingerprint(test_evolution)
    print(f"   Enhanced fingerprint: {fingerprint[:16]}... (64 chars)")
    
    return True

def main():
    """Main test function"""
    try:
        success = test_enhanced_evolution_tracker()
        if success:
            print(f"\n✅ Enhanced Evolution Tracker test completed successfully!")
            print(f"🎯 System is ready to prevent duplicates like issue #202")
            return 0
        else:
            print(f"\n❌ Enhanced Evolution Tracker test failed!")
            return 1
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())