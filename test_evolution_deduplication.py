#!/usr/bin/env python3
"""
Comprehensive Test Suite for Enhanced Evolution Deduplication System

Tests the multi-layer duplicate detection capabilities to prevent
the "5 consecutive performance_optimization" scenario.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Add the src directory to the path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.evolution_tracker import EvolutionTracker


class TestEvolutionDeduplication(unittest.TestCase):
    """Test suite for evolution deduplication system"""
    
    def setUp(self):
        """Set up test environment with temporary directory"""
        self.test_dir = tempfile.mkdtemp()
        self.tracker = EvolutionTracker(evolutions_dir=self.test_dir)
        
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_enhanced_fingerprinting_1000_chars(self):
        """Test that fingerprinting uses 1000 chars vs old 200 chars"""
        # Create evolution with long description
        long_description = "performance optimization " * 100  # > 1000 chars
        evolution = {
            "type": "feature",
            "feature": "performance_optimization",
            "description": long_description,
            "timestamp": datetime.now().isoformat()
        }
        
        fingerprint = self.tracker._generate_fingerprint(evolution)
        
        # Verify fingerprint is 64 chars (enhanced) vs 32 chars (old)
        self.assertEqual(len(fingerprint), 64)
        
        # Verify it includes more content by checking if different long descriptions
        # produce different fingerprints
        evolution2 = evolution.copy()
        evolution2["description"] = "different optimization " * 100
        fingerprint2 = self.tracker._generate_fingerprint(evolution2)
        
        self.assertNotEqual(fingerprint, fingerprint2)
    
    def test_time_window_grouping(self):
        """Test that fingerprinting includes hour-based time grouping"""
        base_evolution = {
            "type": "feature", 
            "feature": "performance_optimization",
            "description": "test optimization"
        }
        
        # Same evolution at different hours should have different fingerprints
        time1 = datetime(2025, 7, 10, 10, 30, 0)  # 10:30 AM
        time2 = datetime(2025, 7, 10, 11, 30, 0)  # 11:30 AM
        
        evolution1 = {**base_evolution, "timestamp": time1.isoformat()}
        evolution2 = {**base_evolution, "timestamp": time2.isoformat()}
        
        fingerprint1 = self.tracker._generate_fingerprint(evolution1)
        fingerprint2 = self.tracker._generate_fingerprint(evolution2)
        
        self.assertNotEqual(fingerprint1, fingerprint2)
    
    def test_technology_term_recognition(self):
        """Test enhanced technology term recognition (60+ terms)"""
        evolution_with_tech = {
            "type": "feature",
            "feature": "performance_optimization", 
            "description": "Optimize Docker containers with Redis caching and Kafka messaging",
            "timestamp": datetime.now().isoformat()
        }
        
        evolution_without_tech = {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "General performance improvements for the system",
            "timestamp": datetime.now().isoformat()
        }
        
        fingerprint_with = self.tracker._generate_fingerprint(evolution_with_tech)
        fingerprint_without = self.tracker._generate_fingerprint(evolution_without_tech)
        
        # Should be different due to technology terms
        self.assertNotEqual(fingerprint_with, fingerprint_without)
    
    def test_performance_specific_extraction(self):
        """Test specific performance area extraction"""
        text_database = "optimize database queries and connection pooling"
        text_memory = "fix memory leaks and garbage collection issues"
        
        db_specifics = self.tracker._extract_performance_specifics(text_database)
        memory_specifics = self.tracker._extract_performance_specifics(text_memory)
        
        self.assertIn("perf_area:database", db_specifics)
        self.assertIn("perf_area:memory", memory_specifics)
        self.assertNotEqual(db_specifics, memory_specifics)
    
    def test_layer1_fingerprint_detection(self):
        """Test Layer 1: Primary fingerprint-based detection"""
        evolution = {
            "type": "feature",
            "feature": "performance_optimization", 
            "description": "Test optimization",
            "timestamp": datetime.now().isoformat()
        }
        
        # First addition should succeed
        self.assertTrue(self.tracker.add_evolution(evolution))
        
        # Exact duplicate should be detected
        self.assertTrue(self.tracker.is_duplicate(evolution))
    
    def test_layer2_time_based_detection(self):
        """Test Layer 2: Time-based duplicate detection (60-minute window)"""
        base_time = datetime.now()
        
        evolution1 = {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "First optimization attempt",
            "timestamp": base_time.isoformat()
        }
        
        # Add first evolution
        self.assertTrue(self.tracker.add_evolution(evolution1))
        
        # Different content but same feature within 60 minutes = duplicate
        evolution2 = {
            "type": "feature", 
            "feature": "performance_optimization",
            "description": "Second optimization attempt with different description",
            "timestamp": (base_time + timedelta(minutes=30)).isoformat()
        }
        
        self.assertTrue(self.tracker._check_time_based_duplicates(evolution2))
        
        # Same feature after 60 minutes should NOT be duplicate
        evolution3 = {
            "type": "feature",
            "feature": "performance_optimization", 
            "description": "Third optimization attempt after time window",
            "timestamp": (base_time + timedelta(minutes=70)).isoformat()
        }
        
        self.assertFalse(self.tracker._check_time_based_duplicates(evolution3))
    
    def test_layer3_semantic_similarity(self):
        """Test Layer 3: Semantic similarity analysis"""
        evolution1 = {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Optimize system performance",
            "timestamp": datetime.now().isoformat()
        }
        
        self.tracker.add_evolution(evolution1)
        
        # Similar feature should be detected
        evolution2 = {
            "type": "feature",
            "feature": "optimization_enhancement", 
            "description": "Different description",
            "timestamp": datetime.now().isoformat()
        }
        
        self.assertTrue(self.tracker._check_semantic_similarity(evolution2))
    
    def test_layer4_text_similarity(self):
        """Test Layer 4: Text similarity using Jaccard coefficient"""
        evolution1 = {
            "type": "feature",
            "feature": "custom_feature_1",
            "description": "implement caching system with redis for better performance optimization",
            "timestamp": datetime.now().isoformat()
        }
        
        self.tracker.add_evolution(evolution1)
        
        # High text similarity (>60%) should be detected
        evolution2 = {
            "type": "feature", 
            "feature": "custom_feature_2",
            "description": "implement caching system with redis for improved performance optimization",
            "timestamp": datetime.now().isoformat()
        }
        
        self.assertTrue(self.tracker._check_text_similarity(evolution2))
        
        # Low text similarity should NOT be detected
        evolution3 = {
            "type": "feature",
            "feature": "custom_feature_3", 
            "description": "create user authentication system with JWT tokens",
            "timestamp": datetime.now().isoformat()
        }
        
        self.assertFalse(self.tracker._check_text_similarity(evolution3))
    
    def test_prevention_of_consecutive_performance_optimizations(self):
        """Test prevention of the specific '5 consecutive performance_optimization' scenario"""
        base_time = datetime.now()
        
        # First performance optimization should succeed
        evolution1 = {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Initial performance optimization with database improvements",
            "timestamp": base_time.isoformat()
        }
        self.assertTrue(self.tracker.add_evolution(evolution1))
        
        # Attempts 2-5 within time window should be blocked
        for i in range(2, 6):
            evolution = {
                "type": "feature",
                "feature": "performance_optimization", 
                "description": f"Performance optimization attempt #{i} with different focus",
                "timestamp": (base_time + timedelta(minutes=i*10)).isoformat()
            }
            
            # Should be detected as duplicate
            self.assertTrue(self.tracker.is_duplicate(evolution))
            
            # Should NOT be added to tracker
            self.assertFalse(self.tracker.add_evolution(evolution))
        
        # Verify only 1 evolution was actually added
        summary = self.tracker.get_evolution_summary()
        perf_count = summary.get("feature_distribution", {}).get("performance_optimization", 0)
        self.assertEqual(perf_count, 1)
    
    def test_different_legitimate_evolutions_allowed(self):
        """Test that different legitimate evolutions are still allowed"""
        base_time = datetime.now()
        
        evolutions = [
            {
                "type": "feature",
                "feature": "security_enhancement",
                "description": "Add authentication and authorization system",
                "timestamp": base_time.isoformat()
            },
            {
                "type": "feature", 
                "feature": "testing_framework",
                "description": "Implement comprehensive unit testing suite",
                "timestamp": (base_time + timedelta(minutes=10)).isoformat()
            },
            {
                "type": "feature",
                "feature": "user_interface", 
                "description": "Create responsive web interface with React",
                "timestamp": (base_time + timedelta(minutes=20)).isoformat()
            }
        ]
        
        # All should be successfully added
        for evolution in evolutions:
            self.assertFalse(self.tracker.is_duplicate(evolution))
            self.assertTrue(self.tracker.add_evolution(evolution))
        
        # Verify all were added
        summary = self.tracker.get_evolution_summary() 
        self.assertEqual(summary["total_evolutions"], 3)
    
    def test_duplicate_analysis_functionality(self):
        """Test comprehensive duplicate analysis functionality"""
        # Add some duplicates for analysis
        base_time = datetime.now()
        
        # Add original
        original = {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Original performance optimization",
            "timestamp": base_time.isoformat()
        }
        self.tracker.add_evolution(original)
        
        # Try to add duplicates (should be blocked)
        for i in range(3):
            duplicate = {
                "type": "feature", 
                "feature": "performance_optimization",
                "description": f"Duplicate performance optimization #{i+1}",
                "timestamp": (base_time + timedelta(minutes=i*15)).isoformat()
            }
            
            # Should be detected and blocked
            self.assertTrue(self.tracker.is_duplicate(duplicate))
            self.assertFalse(self.tracker.add_evolution(duplicate))
        
        # Test that analysis works
        summary = self.tracker.get_evolution_summary()
        self.assertEqual(summary["total_evolutions"], 1)
        self.assertTrue(summary["duplicate_prevention_active"])


class TestEvolutionTrackerIntegration(unittest.TestCase):
    """Integration tests for the complete evolution tracking system"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.tracker = EvolutionTracker(evolutions_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up integration test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_historical_evolution_analysis(self):
        """Test analysis of historical evolution patterns"""
        # Simulate the problematic scenario from the issue
        base_time = datetime(2025, 7, 9, 10, 0, 0)
        
        # Add 5 consecutive performance optimizations (should only allow 1)
        perf_optimizations = []
        for i in range(5):
            evolution = {
                "type": "feature",
                "feature": "performance_optimization",
                "description": f"Performance optimization attempt {i+1}: {['database', 'memory', 'cpu', 'network', 'cache'][i]} improvements",
                "timestamp": (base_time + timedelta(minutes=i*10)).isoformat()
            }
            perf_optimizations.append(evolution)
        
        # Only first should be added
        added_count = 0
        for evolution in perf_optimizations:
            if self.tracker.add_evolution(evolution):
                added_count += 1
        
        # Should only have added 1 out of 5 attempts
        self.assertEqual(added_count, 1)
        
        # Verify summary reflects this
        summary = self.tracker.get_evolution_summary()
        perf_count = summary.get("feature_distribution", {}).get("performance_optimization", 0)
        self.assertEqual(perf_count, 1)
    
    def test_evolution_validation_system(self):
        """Test the evolution validation system"""
        # Valid evolution
        valid_evolution = {
            "type": "feature",
            "feature": "security_enhancement", 
            "description": "Implement comprehensive authentication system with multi-factor support"
        }
        self.assertTrue(self.tracker.add_evolution(valid_evolution))
        
        # Invalid evolutions
        invalid_evolutions = [
            {"type": "invalid_type", "feature": "test", "description": "test"},  # Invalid type
            {"type": "feature", "feature": "", "description": "test"},  # Empty feature
            {"type": "feature", "feature": "test", "description": ""},  # Empty description
            {"type": "feature", "feature": "test", "description": "short"},  # Too short description
        ]
        
        for invalid_evo in invalid_evolutions:
            self.assertFalse(self.tracker.add_evolution(invalid_evo))
    
    def test_impact_scoring_system(self):
        """Test the impact scoring system works correctly"""
        high_impact = {
            "type": "security",
            "feature": "security_enhancement",
            "description": "Critical security vulnerability fix with authentication improvements",
            "priority": "high"
        }
        
        low_impact = {
            "type": "documentation", 
            "feature": "readme_update",
            "description": "Update readme file with basic information",
            "priority": "low"
        }
        
        self.tracker.add_evolution(high_impact)
        self.tracker.add_evolution(low_impact)
        
        evolutions = self.tracker.get_recent_evolutions(2)
        
        # High impact should have higher score than low impact
        high_score = next(e for e in evolutions if e["feature"] == "security_enhancement")["impact_score"]
        low_score = next(e for e in evolutions if e["feature"] == "readme_update")["impact_score"]
        
        self.assertGreater(high_score, low_score)


def run_comprehensive_tests():
    """Run the comprehensive test suite and return results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestEvolutionDeduplication))
    suite.addTests(loader.loadTestsFromTestCase(TestEvolutionTrackerIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    print("🧪 Running Enhanced Evolution Deduplication Test Suite")
    print("=" * 60)
    
    result = run_comprehensive_tests()
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results Summary:")
    print(f"   Tests Run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print(f"\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('\\n')[-2]}")
    
    if not result.failures and not result.errors:
        print("\n✅ All tests passed! Enhanced Evolution Deduplication System is working correctly.")
        print("   The system should now prevent the '5 consecutive performance_optimization' scenario.")
    
    exit(0 if not result.failures and not result.errors else 1)