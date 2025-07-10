#!/usr/bin/env python3
"""
Analyze Current Evolution History for Duplicates
This script analyzes the existing evolution history to identify duplicate patterns
and demonstrates the impact of the enhanced deduplication improvements.
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.evolution_tracker import EvolutionTracker


def analyze_current_evolution_history():
    """Analyze the current evolution history for duplicates"""
    print("🔍 Analyzing Current Evolution History")
    print("=" * 60)
    
    # Load the actual evolution tracker
    tracker = EvolutionTracker()
    
    # Get evolution summary
    summary = tracker.get_evolution_summary()
    
    print("📊 Evolution Summary:")
    print(f"  Total evolutions: {summary['total_evolutions']}")
    print(f"  Evolution types: {summary['evolution_types']}")
    
    if summary['last_evolution']:
        print(f"  Last evolution: {summary['last_evolution'].get('id', 'N/A')}")
        print(f"  Last evolution timestamp: {summary['last_evolution'].get('timestamp', 'N/A')}")
    
    print("\n🔍 Duplicate Analysis:")
    print("-" * 40)
    
    # Run duplicate analysis
    analysis = tracker.analyze_duplicates()
    
    print(f"  Total evolutions analyzed: {analysis['total_evolutions']}")
    print(f"  Duplicate pairs found: {analysis['duplicate_pairs']}")
    
    print("\n📈 Feature Distribution:")
    print("-" * 40)
    
    for feature, count in analysis['most_duplicated_features']:
        print(f"  {feature}: {count} evolutions")
        if count > 3:
            print(f"    ⚠️  Potential duplicate issue with {feature}")
    
    if analysis['duplicates_detail']:
        print("\n🔍 Duplicate Details:")
        print("-" * 40)
        
        for i, duplicate in enumerate(analysis['duplicates_detail'][:10]):  # Show first 10
            print(f"  Duplicate {i+1}:")
            print(f"    Feature: {duplicate['feature']}")
            print(f"    Evolution 1: {duplicate['evolution1']} ({duplicate['timestamp1']})")
            print(f"    Evolution 2: {duplicate['evolution2']} ({duplicate['timestamp2']})")
            print(f"    Time difference: {duplicate['time_diff_minutes']:.1f} minutes")
            print(f"    Similarity: {duplicate['similarity']:.2f}")
            print()
    
    print("\n📅 Timeline Analysis:")
    print("-" * 40)
    
    # Group evolutions by date
    date_groups = {}
    for evolution in tracker.history["evolutions"]:
        try:
            timestamp = evolution.get("timestamp", "")
            date = datetime.fromisoformat(timestamp).date()
            if date not in date_groups:
                date_groups[date] = []
            date_groups[date].append(evolution)
        except (ValueError, TypeError):
            continue
    
    # Find dates with multiple evolutions
    high_activity_dates = [(date, evolutions) for date, evolutions in date_groups.items() if len(evolutions) > 3]
    high_activity_dates.sort(key=lambda x: len(x[1]), reverse=True)
    
    print("  High activity dates (>3 evolutions):")
    for date, evolutions in high_activity_dates[:5]:
        print(f"    {date}: {len(evolutions)} evolutions")
        
        # Check for same-feature duplicates on this date
        feature_counts = {}
        for evo in evolutions:
            feature = evo.get("feature", "unknown")
            feature_counts[feature] = feature_counts.get(feature, 0) + 1
        
        for feature, count in feature_counts.items():
            if count > 1:
                print(f"      ⚠️  {feature}: {count} times (potential duplicates)")
    
    print("\n🎯 Recommendations:")
    print("-" * 40)
    
    if analysis['duplicate_pairs'] > 0:
        print("  ⚠️  Duplicates detected in evolution history!")
        print("  📝 Recommended actions:")
        print("    1. Enhanced deduplication is now active for new evolutions")
        print("    2. Consider cleaning up historical duplicates")
        print("    3. Monitor future evolution creation for duplicate prevention")
        
        # Check for specific problematic patterns
        performance_count = analysis['feature_counts'].get('performance_optimization', 0)
        if performance_count > 5:
            print(f"    4. ⚠️  'performance_optimization' has {performance_count} evolutions")
            print("       This indicates the main duplicate issue identified in the GitHub issue")
    else:
        print("  ✅ No duplicates detected - evolution history is clean!")
    
    return analysis


def demonstrate_improved_deduplication():
    """Demonstrate how the improved deduplication would handle the current duplicate scenario"""
    print("\n🛠️  Demonstrating Improved Deduplication")
    print("=" * 60)
    
    # Create a test tracker with the new improvements
    test_dir = Path(__file__).parent / "test_data" / "evolutions_demo"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    tracker = EvolutionTracker(str(test_dir))
    tracker.history = {
        "evolutions": [],
        "fingerprints": set(),
        "created_at": datetime.now().isoformat()
    }
    
    # Simulate the problematic scenario: 5 performance_optimization evolutions
    print("🧪 Testing scenario: 5 consecutive performance_optimization evolutions")
    print("-" * 60)
    
    performance_evolutions = [
        {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Implement performance monitoring and metrics collection for the debate system",
            "decision_text": "Performance tracking is essential for system optimization and bottleneck identification"
        },
        {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Add performance monitoring with real-time metrics and alerting",
            "decision_text": "Real-time performance tracking will help identify bottlenecks quickly"
        },
        {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Implement performance monitoring system",
            "decision_text": "Performance monitoring needed for system health"
        },
        {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Create performance optimization framework with monitoring",
            "decision_text": "Framework for performance improvements across the system"
        },
        {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Add performance profiling and optimization tools",
            "decision_text": "Profiling tools will help identify performance issues"
        }
    ]
    
    print("Results with enhanced deduplication:")
    accepted = 0
    rejected = 0
    
    for i, evolution in enumerate(performance_evolutions):
        result = tracker.add_evolution(evolution)
        if result:
            accepted += 1
            print(f"  Evolution {i+1}: ✅ ACCEPTED")
        else:
            rejected += 1
            print(f"  Evolution {i+1}: ❌ REJECTED (duplicate detected)")
    
    print(f"\nSummary:")
    print(f"  ✅ Accepted: {accepted}")
    print(f"  ❌ Rejected: {rejected}")
    print(f"  🎯 Duplicate prevention: {rejected}/{len(performance_evolutions)} evolutions blocked")
    
    if rejected > 0:
        print(f"  🎉 SUCCESS: Enhanced deduplication prevented {rejected} duplicate evolutions!")
    
    # Show the fingerprint differences
    print("\n🔍 Fingerprint Analysis:")
    print("-" * 40)
    
    fingerprints = []
    for i, evolution in enumerate(performance_evolutions):
        fp = tracker._generate_fingerprint(evolution)
        fingerprints.append(fp)
        print(f"  Evolution {i+1} fingerprint: {fp[:16]}...")
    
    unique_fingerprints = set(fingerprints)
    print(f"\nUnique fingerprints: {len(unique_fingerprints)}/{len(fingerprints)}")
    
    if len(unique_fingerprints) < len(fingerprints):
        print("  ⚠️  Some evolutions have identical fingerprints (correctly identified as duplicates)")
    else:
        print("  ✅ All evolutions have unique fingerprints")
    
    return {
        "accepted": accepted,
        "rejected": rejected,
        "total": len(performance_evolutions),
        "unique_fingerprints": len(unique_fingerprints)
    }


if __name__ == "__main__":
    try:
        print("🚀 Evolution History Analysis and Improvement Demonstration")
        print("=" * 80)
        
        # Analyze current history
        analysis = analyze_current_evolution_history()
        
        # Demonstrate improvements
        improvement_results = demonstrate_improved_deduplication()
        
        print("\n" + "=" * 80)
        print("📋 Final Report:")
        print("=" * 80)
        
        print(f"Current evolution history contains {analysis['duplicate_pairs']} duplicate pairs")
        print(f"Enhanced deduplication prevented {improvement_results['rejected']} duplicates in test scenario")
        
        if analysis['duplicate_pairs'] > 0:
            print("\n🎯 The ONE most important improvement implemented:")
            print("   Enhanced Evolution Deduplication System")
            print("   - Time-based duplicate prevention")
            print("   - Semantic similarity detection")
            print("   - Enhanced fingerprinting with specific content extraction")
            print("   - 5x more content analyzed (1000 vs 200 characters)")
            print("   - Automatic evolution variation generation")
            
            effectiveness = (improvement_results['rejected'] / improvement_results['total']) * 100
            print(f"\n📊 Effectiveness: {effectiveness:.1f}% of duplicates prevented in test scenario")
        
        print("\n✅ Analysis completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)