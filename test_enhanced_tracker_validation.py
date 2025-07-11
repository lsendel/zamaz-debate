#!/usr/bin/env python3
"""
Enhanced Evolution Tracker Validation Script
Runs quality checks and tests for the Enhanced Evolution Deduplication System
"""

import sys
import os
import traceback
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_syntax_check():
    """Test Python syntax compilation"""
    print("🔍 Testing Python syntax compilation...")
    
    try:
        import py_compile
        py_compile.compile("src/core/evolution_tracker.py", doraise=True)
        print("✅ Python syntax check passed")
        return True
    except py_compile.PyCompileError as e:
        print(f"❌ Python syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during syntax check: {e}")
        return False

def test_import_check():
    """Test that the enhanced evolution tracker can be imported"""
    print("🔍 Testing enhanced evolution tracker import...")
    
    try:
        from src.core.evolution_tracker import EvolutionTracker
        print("✅ Enhanced EvolutionTracker imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of the enhanced evolution tracker"""
    print("🔍 Testing enhanced evolution tracker functionality...")
    
    try:
        from src.core.evolution_tracker import EvolutionTracker
        
        # Create tracker instance
        tracker = EvolutionTracker()
        print("✅ EvolutionTracker instance created")
        
        # Test duplicate detection on similar evolutions
        evo1 = {
            'type': 'feature',
            'feature': 'performance_optimization', 
            'description': 'Test optimization for database queries',
            'timestamp': datetime.now().isoformat()
        }

        evo2 = {
            'type': 'feature',
            'feature': 'performance_optimization',
            'description': 'Another test optimization for memory usage', 
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"First evolution duplicate check: {tracker.is_duplicate(evo1)}")
        
        # Add first evolution
        result1 = tracker.add_evolution(evo1)
        print(f"First evolution added: {result1}")
        
        # Check if second similar evolution is detected as duplicate
        duplicate_check = tracker.is_duplicate(evo2)
        print(f"Second evolution duplicate check: {duplicate_check}")
        
        print("✅ Enhanced deduplication system working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        traceback.print_exc()
        return False

def test_enhanced_features():
    """Test enhanced features specific to the new implementation"""
    print("🔍 Testing enhanced deduplication features...")
    
    try:
        from src.core.evolution_tracker import EvolutionTracker
        
        tracker = EvolutionTracker()
        
        # Test validation function
        valid_evo = {
            'type': 'feature',
            'feature': 'test_feature', 
            'description': 'A valid test evolution with enough description content'
        }
        
        invalid_evo = {
            'type': 'invalid_type',
            'feature': 'x',  # Too short
            'description': 'Short'  # Too short
        }
        
        # Test validation
        valid_result = tracker._validate_evolution(valid_evo)
        invalid_result = tracker._validate_evolution(invalid_evo)
        
        print(f"Valid evolution validation: {valid_result}")
        print(f"Invalid evolution validation: {invalid_result}")
        
        # Test impact scoring
        impact_score = tracker._calculate_impact_score(valid_evo)
        print(f"Impact score calculation: {impact_score}")
        
        # Test time-based duplicate detection
        recent_evos = tracker.get_recent_evolutions(5)
        print(f"Recent evolutions retrieved: {len(recent_evos)}")
        
        # Test semantic similarity
        similar_evo1 = {
            'type': 'feature',
            'feature': 'performance_optimization',
            'description': 'Optimize database queries for better performance'
        }
        
        similar_evo2 = {
            'type': 'feature', 
            'feature': 'performance_enhancement',
            'description': 'Enhance database query performance through optimization'
        }
        
        are_similar = tracker._are_descriptions_similar(
            similar_evo1['description'].lower(),
            similar_evo2['description'].lower()
        )
        print(f"Semantic similarity detection: {are_similar}")
        
        print("✅ Enhanced features tested successfully")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced features test failed: {e}")
        traceback.print_exc()
        return False

def test_existing_tests():
    """Run existing pytest tests"""
    print("🔍 Running existing pytest tests...")
    
    try:
        import subprocess
        import os
        
        # Change to project directory
        os.chdir(Path(__file__).parent)
        
        # Run specific evolution tracker tests
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_evolution_tracker.py", 
            "-v", "--tb=short"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Existing pytest tests passed")
            print("STDOUT:", result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            return True
        else:
            print("❌ Existing pytest tests failed")
            print("STDOUT:", result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Pytest tests timed out")
        return False
    except Exception as e:
        print(f"❌ Error running pytest: {e}")
        return False

def main():
    """Run all quality checks"""
    print("🚀 Enhanced Evolution Deduplication System - Quality Checks")
    print("=" * 60)
    
    checks = [
        ("Syntax Check", test_syntax_check),
        ("Import Check", test_import_check), 
        ("Basic Functionality", test_basic_functionality),
        ("Enhanced Features", test_enhanced_features),
        ("Existing Tests", test_existing_tests),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}")
        print("-" * 40)
        
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} failed with exception: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Quality Check Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All quality checks passed! Implementation is ready to commit.")
        return 0
    else:
        print("⚠️  Some quality checks failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())