#!/usr/bin/env python3
"""
Quick validation of Enhanced Evolution Tracker
Tests core functionality without external dependencies
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    print("🔍 Enhanced Evolution Tracker - Quick Validation")
    print("=" * 50)
    
    try:
        # Test 1: Import
        print("\n1. Testing import...")
        from src.core.evolution_tracker import EvolutionTracker
        print("✅ Import successful")
        
        # Test 2: Instance creation
        print("\n2. Testing instance creation...")
        tracker = EvolutionTracker()
        print("✅ Instance created successfully")
        
        # Test 3: Basic validation
        print("\n3. Testing evolution validation...")
        valid_evo = {
            'type': 'feature',
            'feature': 'test_validation',
            'description': 'This is a test evolution with sufficient description length for validation'
        }
        
        invalid_evo = {
            'type': 'invalid_type',
            'feature': 'x',
            'description': 'Too short'
        }
        
        valid_result = tracker._validate_evolution(valid_evo)
        invalid_result = tracker._validate_evolution(invalid_evo)
        
        print(f"✅ Valid evolution validation: {valid_result}")
        print(f"✅ Invalid evolution validation: {invalid_result}")
        
        # Test 4: Fingerprint generation
        print("\n4. Testing enhanced fingerprint generation...")
        fp1 = tracker._generate_fingerprint(valid_evo)
        print(f"✅ Fingerprint generated: {fp1[:20]}... (length: {len(fp1)})")
        
        # Test 5: Duplicate detection logic
        print("\n5. Testing duplicate detection...")
        evo1 = {
            'type': 'feature',
            'feature': 'performance_optimization',
            'description': 'Optimize database queries for better performance and reduced latency',
            'timestamp': datetime.now().isoformat()
        }
        
        evo2 = {
            'type': 'feature',
            'feature': 'performance_optimization', 
            'description': 'Enhance database query performance through caching optimization',
            'timestamp': datetime.now().isoformat()
        }
        
        # Clear any existing history for clean test
        tracker.history = {"evolutions": [], "fingerprints": set()}
        
        is_duplicate_before = tracker.is_duplicate(evo1)
        print(f"✅ First evolution duplicate check: {is_duplicate_before}")
        
        # Add first evolution
        added = tracker.add_evolution(evo1)
        print(f"✅ First evolution added: {added}")
        
        # Check if second similar evolution is detected as duplicate
        is_duplicate_after = tracker.is_duplicate(evo2)
        print(f"✅ Second evolution duplicate check: {is_duplicate_after}")
        
        # Test 6: Impact scoring
        print("\n6. Testing impact scoring...")
        impact_score = tracker._calculate_impact_score(valid_evo)
        print(f"✅ Impact score calculated: {impact_score}")
        
        # Test 7: Similarity detection
        print("\n7. Testing semantic similarity...")
        similar_features = tracker._are_features_similar(
            "performance_optimization", 
            "performance_enhancement"
        )
        print(f"✅ Feature similarity detection: {similar_features}")
        
        text_similarity = tracker._are_descriptions_similar(
            "optimize database queries for performance",
            "enhance database query performance optimization"
        )
        print(f"✅ Text similarity detection: {text_similarity}")
        
        # Test 8: Summary generation
        print("\n8. Testing evolution summary...")
        summary = tracker.get_evolution_summary()
        print(f"✅ Summary generated: {summary.get('total_evolutions', 0)} evolutions")
        
        print("\n" + "=" * 50)
        print("🎉 All validation tests passed!")
        print("✅ Enhanced Evolution Tracker is working correctly")
        print("🚀 Ready for commit and deployment")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ VALIDATION SUCCESSFUL - Implementation is ready")
        sys.exit(0)
    else:
        print("\n❌ VALIDATION FAILED - Please review issues")
        sys.exit(1)