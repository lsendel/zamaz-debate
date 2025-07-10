#!/usr/bin/env python3
"""
Run integration tests for cross-context communication.

This script runs all integration tests and provides a summary of results.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_tests():
    """Run all integration tests"""
    print("=" * 80)
    print("Running Cross-Context Integration Tests")
    print("=" * 80)
    print()
    
    # Test files to run
    test_files = [
        "tests/integration/test_event_bus.py",
        "tests/integration/test_cross_context_flows.py",
        "tests/integration/test_saga_patterns.py",
    ]
    
    # Ensure test directory exists
    Path("tests/integration").mkdir(parents=True, exist_ok=True)
    
    results = {}
    total_start = time.time()
    
    for test_file in test_files:
        print(f"\n{'=' * 60}")
        print(f"Running: {test_file}")
        print(f"{'=' * 60}")
        
        start_time = time.time()
        
        # Run pytest with verbose output
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            test_file,
            "-v",
            "--tb=short",
            "--no-header",
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        duration = time.time() - start_time
        
        # Store results
        results[test_file] = {
            "returncode": result.returncode,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        
        # Print output
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        print(f"\nDuration: {duration:.2f} seconds")
    
    total_duration = time.time() - total_start
    
    # Print summary
    print(f"\n{'=' * 80}")
    print("INTEGRATION TEST SUMMARY")
    print(f"{'=' * 80}")
    print(f"\nTotal Duration: {total_duration:.2f} seconds")
    print("\nResults:")
    
    all_passed = True
    for test_file, result in results.items():
        status = "PASSED" if result["returncode"] == 0 else "FAILED"
        if result["returncode"] != 0:
            all_passed = False
        
        print(f"  {test_file:<50} {status:>10} ({result['duration']:.2f}s)")
    
    print(f"\n{'=' * 80}")
    
    if all_passed:
        print("✅ All integration tests PASSED!")
        return 0
    else:
        print("❌ Some integration tests FAILED!")
        print("\nFailed tests:")
        for test_file, result in results.items():
            if result["returncode"] != 0:
                print(f"  - {test_file}")
        return 1


def main():
    """Main entry point"""
    print("Checking environment...")
    
    # Check if pytest is installed
    try:
        import pytest
        print(f"✓ pytest version: {pytest.__version__}")
    except ImportError:
        print("✗ pytest not installed. Run: pip install pytest pytest-asyncio")
        return 1
    
    # Check if project modules are importable
    try:
        import src.events
        print("✓ Project modules importable")
    except ImportError as e:
        print(f"✗ Cannot import project modules: {e}")
        print("  Make sure you're running from the project root directory")
        return 1
    
    print()
    
    # Run tests
    return run_tests()


if __name__ == "__main__":
    sys.exit(main())