#!/usr/bin/env python3
"""
Test script to validate how the Enhanced Evolution Tracker would have 
prevented the historical duplicates found in issue #202
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_historical_duplicate_prevention():
    """Test how enhanced system would prevent historical duplicates"""
    print("🕰️  Testing Historical Duplicate Prevention")
    print("=" * 60)
    
    try:
        from src.core.evolution_tracker import EvolutionTracker
        
        # Create a fresh tracker for testing
        tracker = EvolutionTracker()
        print("✅ Test tracker created")
        
        # Load historical problematic evolutions
        evolutions_dir = Path("data/evolutions")
        problem_files = [
            "evo_54_20250708_030530.json",
            "evo_55_20250708_030546.json", 
            "evo_56_20250708_030601.json",
        ]
        
        print(f"\n🔍 Testing with {len(problem_files)} known duplicate files:")
        
        test_results = []
        
        for i, filename in enumerate(problem_files):
            file_path = evolutions_dir / filename
            if not file_path.exists():
                print(f"   ⚠️  File not found: {filename}")
                continue
                
            with open(file_path, 'r') as f:
                evolution = json.load(f)
            
            print(f"\n   📁 Testing: {filename}")
            print(f"      Feature: {evolution.get('feature', 'unknown')}")
            print(f"      Timestamp: {evolution.get('timestamp', 'unknown')}")
            
            # Test each duplicate detection layer
            if i == 0:
                # First one should be allowed (no duplicates yet)
                is_duplicate = tracker.is_duplicate(evolution)
                print(f"      Result: {'BLOCKED' if is_duplicate else 'ALLOWED'} (first one)")
                
                # Add it to the tracker for subsequent tests
                if not is_duplicate:
                    tracker.history["evolutions"].append(evolution)
                    fingerprint = tracker._generate_fingerprint(evolution)
                    tracker.history["fingerprints"].add(fingerprint)
                    
            else:
                # Subsequent ones should be blocked
                is_duplicate = tracker.is_duplicate(evolution)
                print(f"      Result: {'✅ BLOCKED' if is_duplicate else '❌ ALLOWED'} (duplicate check)")
                
                # Test individual layers
                if hasattr(tracker, '_check_time_based_duplicates'):
                    time_dup = tracker._check_time_based_duplicates(evolution)
                    print(f"         Layer 2 (Time): {'DETECTED' if time_dup else 'missed'}")
                
                if hasattr(tracker, '_check_semantic_similarity'):
                    semantic_dup = tracker._check_semantic_similarity(evolution)
                    print(f"         Layer 3 (Semantic): {'DETECTED' if semantic_dup else 'missed'}")
                
                if hasattr(tracker, '_check_text_similarity'):
                    text_dup = tracker._check_text_similarity(evolution)
                    print(f"         Layer 4 (Text): {'DETECTED' if text_dup else 'missed'}")
            
            test_results.append({
                'file': filename,
                'feature': evolution.get('feature'),
                'blocked': is_duplicate if i > 0 else False,
                'expected_blocked': i > 0
            })
        
        # Summary
        print(f"\n📊 Prevention Test Results:")
        prevented_count = sum(1 for r in test_results if r['blocked'] and r['expected_blocked'])
        should_prevent_count = sum(1 for r in test_results if r['expected_blocked'])
        
        print(f"   Duplicates that should be prevented: {should_prevent_count}")
        print(f"   Duplicates actually prevented: {prevented_count}")
        print(f"   Prevention rate: {(prevented_count/should_prevent_count*100) if should_prevent_count > 0 else 0:.1f}%")
        
        if prevented_count == should_prevent_count:
            print(f"   ✅ Perfect prevention! All duplicates would be blocked.")
        else:
            print(f"   ⚠️  Some duplicates would slip through.")
            
        return prevented_count == should_prevent_count
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rapid_creation_simulation():
    """Simulate rapid creation scenario like in issue #202"""
    print(f"\n⚡ Testing Rapid Creation Prevention")
    print("-" * 40)
    
    try:
        from src.core.evolution_tracker import EvolutionTracker
        
        tracker = EvolutionTracker()
        
        # Simulate creating 5 performance optimizations in rapid succession
        base_time = datetime.now()
        
        blocked_count = 0
        
        for i in range(5):
            # Create evolution with timestamps 30 seconds apart
            timestamp = base_time.replace(second=base_time.second + (i * 30))
            
            evolution = {
                "type": "feature",
                "feature": "performance_optimization",
                "description": f"Performance optimization attempt {i+1}",
                "timestamp": timestamp.isoformat()
            }
            
            is_duplicate = tracker.is_duplicate(evolution)
            
            print(f"   Attempt {i+1}: {'BLOCKED' if is_duplicate else 'ALLOWED'}")
            
            if is_duplicate:
                blocked_count += 1
            else:
                # Add to tracker if allowed
                tracker.history["evolutions"].append(evolution)
                fingerprint = tracker._generate_fingerprint(evolution)
                tracker.history["fingerprints"].add(fingerprint)
        
        prevention_rate = (blocked_count / 4) * 100  # 4 should be blocked (first is allowed)
        print(f"\n   📈 Rapid creation prevention: {blocked_count}/4 blocked ({prevention_rate:.1f}%)")
        
        return blocked_count >= 3  # At least 3 of 4 duplicates should be blocked
        
    except Exception as e:
        print(f"❌ Rapid creation test failed: {e}")
        return False

def main():
    """Main test function"""
    try:
        print("🎯 Enhanced Evolution Deduplication System - Historical Validation")
        print("=" * 70)
        
        # Test historical prevention
        historical_success = test_historical_duplicate_prevention()
        
        # Test rapid creation prevention
        rapid_success = test_rapid_creation_simulation()
        
        print(f"\n📋 Final Results:")
        print(f"   Historical duplicate prevention: {'✅ PASS' if historical_success else '❌ FAIL'}")
        print(f"   Rapid creation prevention: {'✅ PASS' if rapid_success else '❌ FAIL'}")
        
        overall_success = historical_success and rapid_success
        
        if overall_success:
            print(f"\n🎉 SUCCESS: Enhanced system would have prevented issue #202!")
            print(f"💡 The performance_optimization duplicates would be blocked.")
            print(f"⚡ Rapid creation attacks would be thwarted.")
            return 0
        else:
            print(f"\n⚠️  Some issues remain with the enhanced system.")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())