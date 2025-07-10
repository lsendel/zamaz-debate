#!/usr/bin/env python3
"""
Analyze evolution history to identify duplicate patterns and issues
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
from difflib import SequenceMatcher

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.evolution_tracker import EvolutionTracker


def analyze_performance_optimization_duplicates():
    """Analyze the specific performance_optimization duplicates mentioned in the issue"""
    
    print("🔍 Analyzing Performance Optimization Duplicates")
    print("=" * 55)
    
    # Load evolution history
    tracker = EvolutionTracker()
    evolutions = tracker.history.get("evolutions", [])
    
    # Find performance_optimization evolutions
    perf_evolutions = [evo for evo in evolutions if evo.get("feature") == "performance_optimization"]
    
    print(f"Found {len(perf_evolutions)} performance_optimization evolutions")
    
    if not perf_evolutions:
        print("No performance_optimization evolutions found")
        return
    
    # Sort by timestamp
    perf_evolutions.sort(key=lambda x: x.get("timestamp", ""))
    
    # Show the last 5 (the ones mentioned in the issue)
    print(f"\nLast 5 performance_optimization evolutions:")
    for i, evo in enumerate(perf_evolutions[-5:]):
        print(f"\n{i+1}. Evolution ID: {evo.get('id', 'N/A')}")
        print(f"   Timestamp: {evo.get('timestamp', 'N/A')}")
        print(f"   Fingerprint: {evo.get('fingerprint', 'N/A')}")
        print(f"   Debate ID: {evo.get('debate_id', 'N/A')}")
        print(f"   Description length: {len(evo.get('description', ''))}")
        
        # Show first 200 chars of description
        description = evo.get('description', '')
        if description:
            print(f"   Description preview: {description[:200]}...")
    
    # Analyze similarities between the last 5
    print(f"\n📊 Similarity Analysis of Last 5 Performance Optimizations:")
    last_5 = perf_evolutions[-5:]
    
    for i in range(len(last_5)):
        for j in range(i+1, len(last_5)):
            evo1 = last_5[i]
            evo2 = last_5[j]
            
            # Calculate text similarity
            text1 = evo1.get('description', '').lower()
            text2 = evo2.get('description', '').lower()
            
            similarity = SequenceMatcher(None, text1, text2).ratio()
            
            # Calculate time difference
            try:
                time1 = datetime.fromisoformat(evo1.get('timestamp', ''))
                time2 = datetime.fromisoformat(evo2.get('timestamp', ''))
                time_diff = abs((time2 - time1).total_seconds() / 3600)
            except:
                time_diff = 0
            
            print(f"   {evo1.get('id', 'N/A')} vs {evo2.get('id', 'N/A')}: {similarity:.1%} similarity, {time_diff:.1f}h apart")
    
    return perf_evolutions


def analyze_all_duplicates():
    """Analyze all evolutions for duplicate patterns"""
    
    print("\n🔍 Analyzing All Evolution Duplicates")
    print("=" * 40)
    
    tracker = EvolutionTracker()
    evolutions = tracker.history.get("evolutions", [])
    
    print(f"Total evolutions: {len(evolutions)}")
    
    # Group by feature
    feature_groups = defaultdict(list)
    for evo in evolutions:
        feature = evo.get("feature", "unknown")
        feature_groups[feature].append(evo)
    
    print(f"Unique features: {len(feature_groups)}")
    
    # Find features with multiple evolutions
    duplicate_features = {feature: evos for feature, evos in feature_groups.items() if len(evos) > 1}
    
    print(f"\nFeatures with multiple evolutions: {len(duplicate_features)}")
    
    for feature, evos in sorted(duplicate_features.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"   {feature}: {len(evos)} evolutions")
        
        # Show timestamps for rapid duplicates
        timestamps = []
        for evo in evos:
            try:
                ts = datetime.fromisoformat(evo.get("timestamp", ""))
                timestamps.append(ts)
            except:
                continue
        
        if len(timestamps) > 1:
            timestamps.sort()
            min_gap = min((timestamps[i+1] - timestamps[i]).total_seconds() / 3600 
                         for i in range(len(timestamps)-1))
            max_gap = max((timestamps[i+1] - timestamps[i]).total_seconds() / 3600 
                         for i in range(len(timestamps)-1))
            total_span = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
            
            print(f"      Time span: {total_span:.1f}h, Min gap: {min_gap:.1f}h, Max gap: {max_gap:.1f}h")
            
            # Check for rapid duplicates (within 1 hour)
            rapid_count = sum(1 for i in range(len(timestamps)-1) 
                             if (timestamps[i+1] - timestamps[i]).total_seconds() < 3600)
            if rapid_count > 0:
                print(f"      ⚠️  {rapid_count} rapid duplicates (< 1 hour apart)")
    
    return duplicate_features


def analyze_evolution_patterns():
    """Analyze patterns in evolution history"""
    
    print("\n📈 Analyzing Evolution Patterns")
    print("=" * 35)
    
    tracker = EvolutionTracker()
    evolutions = tracker.history.get("evolutions", [])
    
    # Evolution types
    types = Counter(evo.get("type", "unknown") for evo in evolutions)
    print(f"Evolution types:")
    for evo_type, count in types.most_common():
        print(f"   {evo_type}: {count}")
    
    # Most common features
    features = Counter(evo.get("feature", "unknown") for evo in evolutions)
    print(f"\nTop 10 most common features:")
    for feature, count in features.most_common(10):
        print(f"   {feature}: {count}")
    
    # Timeline analysis
    timestamps = []
    for evo in evolutions:
        try:
            ts = datetime.fromisoformat(evo.get("timestamp", ""))
            timestamps.append(ts)
        except:
            continue
    
    if timestamps:
        timestamps.sort()
        print(f"\nTimeline analysis:")
        print(f"   First evolution: {timestamps[0]}")
        print(f"   Last evolution: {timestamps[-1]}")
        print(f"   Total span: {(timestamps[-1] - timestamps[0]).days} days")
        
        # Evolution frequency
        if len(timestamps) > 1:
            total_hours = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
            avg_frequency = total_hours / len(timestamps)
            print(f"   Average frequency: {avg_frequency:.1f} hours between evolutions")
    
    # Fingerprint analysis
    fingerprints = [evo.get("fingerprint") for evo in evolutions if evo.get("fingerprint")]
    unique_fingerprints = len(set(fingerprints))
    
    print(f"\nFingerprint analysis:")
    print(f"   Total fingerprints: {len(fingerprints)}")
    print(f"   Unique fingerprints: {unique_fingerprints}")
    print(f"   Duplicate fingerprints: {len(fingerprints) - unique_fingerprints}")
    
    # Check for actual fingerprint duplicates
    fingerprint_counts = Counter(fingerprints)
    actual_duplicates = {fp: count for fp, count in fingerprint_counts.items() if count > 1}
    
    if actual_duplicates:
        print(f"   Actual duplicate fingerprints:")
        for fp, count in actual_duplicates.items():
            print(f"     {fp}: {count} times")
    
    return {
        "types": types,
        "features": features,
        "timestamps": timestamps,
        "fingerprints": fingerprints,
        "actual_duplicates": actual_duplicates
    }


def test_new_deduplication():
    """Test the new deduplication system on historical data"""
    
    print("\n🧪 Testing New Deduplication System")
    print("=" * 40)
    
    # Create a new tracker instance
    tracker = EvolutionTracker()
    
    # Test the new deduplication methods
    print("Testing enhanced deduplication methods...")
    
    # Get some recent evolutions to test
    recent_evolutions = tracker.get_recent_evolutions(10)
    
    if not recent_evolutions:
        print("No recent evolutions to test")
        return
    
    # Test time-based duplicate detection
    test_evolution = recent_evolutions[0].copy()
    test_evolution['timestamp'] = datetime.now().isoformat()
    
    is_time_duplicate = tracker._is_time_based_duplicate(test_evolution)
    print(f"   Time-based duplicate detection: {is_time_duplicate}")
    
    # Test semantic similarity
    is_semantic_duplicate = tracker._is_semantically_similar(test_evolution)
    print(f"   Semantic similarity detection: {is_semantic_duplicate}")
    
    # Test text similarity
    is_text_duplicate = tracker._is_text_similar(test_evolution)
    print(f"   Text similarity detection: {is_text_duplicate}")
    
    # Test overall duplicate detection
    is_duplicate = tracker.is_duplicate(test_evolution)
    print(f"   Overall duplicate detection: {is_duplicate}")
    
    # Test duplicate analysis
    analysis = tracker.analyze_evolution_duplicates()
    print(f"   Duplicate analysis completed: {analysis['total_evolutions']} evolutions analyzed")
    
    return analysis


def main():
    """Main analysis function"""
    
    print("🔍 Evolution History Analysis")
    print("=" * 30)
    print("Analyzing evolution history to identify duplicate patterns and issues")
    print(f"Analysis started at: {datetime.now()}")
    
    try:
        # Run all analyses
        perf_evolutions = analyze_performance_optimization_duplicates()
        duplicate_features = analyze_all_duplicates()
        patterns = analyze_evolution_patterns()
        new_dedup_test = test_new_deduplication()
        
        # Summary
        print("\n📋 Analysis Summary")
        print("=" * 20)
        print(f"✅ Performance optimization evolutions: {len(perf_evolutions) if perf_evolutions else 0}")
        print(f"✅ Features with duplicates: {len(duplicate_features) if duplicate_features else 0}")
        print(f"✅ Total evolution patterns analyzed: {len(patterns['types']) if patterns else 0}")
        print(f"✅ New deduplication system tested: {'Yes' if new_dedup_test else 'No'}")
        
        print(f"\n🎉 Analysis completed successfully at: {datetime.now()}")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()