#!/usr/bin/env python3
"""
Tests for Enhanced Evolution Tracker v2
"""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import time

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.core.evolution_tracker_v2 import EvolutionTrackerV2


class TestEvolutionTrackerV2:
    """Test suite for enhanced evolution tracker"""
    
    @pytest.fixture
    def tracker(self):
        """Create a tracker with temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield EvolutionTrackerV2(temp_dir)
    
    def test_initialization(self, tracker):
        """Test tracker initialization"""
        assert tracker.history["version"] == "2.0"
        assert tracker.history["duplicate_prevention"] is True
        assert len(tracker.history["evolutions"]) == 0
        assert len(tracker.history["fingerprints"]) == 0
    
    def test_add_evolution(self, tracker):
        """Test adding a valid evolution"""
        evolution = {
            "type": "feature",
            "feature": "test_feature",
            "description": "Test feature description"
        }
        
        result = tracker.add_evolution(evolution)
        assert result is True
        assert len(tracker.history["evolutions"]) == 1
        
        # Check metadata was added
        added_evo = tracker.history["evolutions"][0]
        assert "id" in added_evo
        assert "timestamp" in added_evo
        assert "fingerprint" in added_evo
        assert "version" in added_evo
    
    def test_duplicate_detection_by_fingerprint(self, tracker):
        """Test duplicate detection by fingerprint"""
        evolution = {
            "type": "feature",
            "feature": "duplicate_test",
            "description": "This is a duplicate test"
        }
        
        # Add first time
        assert tracker.add_evolution(evolution) is True
        
        # Try to add again - should be rejected
        assert tracker.add_evolution(evolution) is False
        assert len(tracker.history["evolutions"]) == 1
    
    def test_recent_duplicate_detection(self, tracker):
        """Test detection of recent duplicates (same feature within 24 hours)"""
        evolution1 = {
            "type": "feature",
            "feature": "performance_profiling",
            "description": "Add performance profiling"
        }
        
        evolution2 = {
            "type": "feature",
            "feature": "performance_profiling",
            "description": "Different description but same feature"
        }
        
        # Add first evolution
        assert tracker.add_evolution(evolution1) is True
        
        # Try to add similar evolution immediately - should be rejected
        assert tracker.add_evolution(evolution2) is False
    
    def test_validation(self, tracker):
        """Test evolution validation"""
        # Missing required field
        invalid_evolution = {
            "type": "feature"
            # Missing 'feature' field
        }
        assert tracker.add_evolution(invalid_evolution) is False
        
        # Invalid type
        invalid_type = {
            "type": "invalid_type",
            "feature": "test"
        }
        assert tracker.add_evolution(invalid_type) is False
        
        # Valid evolution
        valid_evolution = {
            "type": "enhancement",
            "feature": "valid_feature",
            "description": "Valid enhancement"
        }
        assert tracker.add_evolution(valid_evolution) is True
    
    def test_enhanced_fingerprinting(self, tracker):
        """Test enhanced fingerprinting with more context"""
        evo1 = {
            "type": "feature",
            "feature": "caching",
            "description": "Add caching for API responses",
            "decision_text": "Implement Redis-based caching"
        }
        
        evo2 = {
            "type": "feature",
            "feature": "caching",
            "description": "Add caching for database queries",
            "decision_text": "Implement query result caching"
        }
        
        # Different descriptions should create different fingerprints
        fp1 = tracker._generate_fingerprint(evo1)
        fp2 = tracker._generate_fingerprint(evo2)
        
        assert fp1 != fp2
        assert len(fp1) == 32  # Longer hash
        assert len(fp2) == 32
    
    def test_version_integration(self, tracker):
        """Test version management integration"""
        # Add a feature (should bump minor version)
        feature = {
            "type": "feature",
            "feature": "new_feature",
            "description": "Add new feature"
        }
        
        initial_version = tracker.version_manager.get_current_version()
        assert tracker.add_evolution(feature) is True
        
        # Check version was recorded
        added_evo = tracker.history["evolutions"][0]
        assert "version" in added_evo
        
        # Version should have been bumped
        new_version = tracker.version_manager.get_current_version()
        assert new_version != initial_version
    
    def test_data_cleanup(self, tracker):
        """Test data integrity validation and cleanup"""
        # Manually add duplicate evolutions to history
        evo = {
            "type": "feature",
            "feature": "test_cleanup",
            "description": "Test cleanup"
        }
        
        # Add same evolution multiple times (simulating bad data)
        tracker.history["evolutions"] = [evo.copy() for _ in range(5)]
        
        # Run cleanup
        tracker._validate_and_cleanup()
        
        # Should have removed duplicates
        assert len(tracker.history["evolutions"]) == 1
    
    def test_get_evolution_summary(self, tracker):
        """Test evolution summary generation"""
        # Add various evolution types
        evolutions = [
            {"type": "feature", "feature": "feature1"},
            {"type": "feature", "feature": "feature2"},
            {"type": "enhancement", "feature": "enhance1"},
            {"type": "fix", "feature": "fix1"}
        ]
        
        for evo in evolutions:
            tracker.add_evolution(evo)
        
        summary = tracker.get_evolution_summary()
        
        assert summary["total_evolutions"] == 4
        assert summary["evolution_types"]["feature"] == 2
        assert summary["evolution_types"]["enhancement"] == 1
        assert summary["evolution_types"]["fix"] == 1
        assert summary["duplicate_prevention"] is True
        assert "current_version" in summary
        assert summary["unique_features"] == 4
    
    def test_thread_safety(self, tracker):
        """Test thread-safe operations"""
        import threading
        
        results = []
        
        def add_evolution(i):
            evolution = {
                "type": "feature",
                "feature": f"thread_feature_{i}",
                "description": f"Thread test {i}"
            }
            result = tracker.add_evolution(evolution)
            results.append(result)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=add_evolution, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # All should succeed
        assert all(results)
        assert len(tracker.history["evolutions"]) == 10
    
    def test_feature_timestamp_tracking(self, tracker):
        """Test feature timestamp tracking"""
        feature_name = "timestamp_test"
        
        evolution = {
            "type": "feature",
            "feature": feature_name,
            "description": "Test timestamp tracking"
        }
        
        # Add evolution
        assert tracker.add_evolution(evolution) is True
        
        # Check timestamp was recorded
        assert feature_name in tracker.history["feature_timestamps"]
        timestamp = tracker.history["feature_timestamps"][feature_name]
        
        # Verify it's a recent timestamp
        recorded_time = datetime.fromisoformat(timestamp)
        assert datetime.now() - recorded_time < timedelta(seconds=5)