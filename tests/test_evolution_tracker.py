"""
Tests for Evolution Tracker
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.core.evolution_tracker import EvolutionTracker


class TestEvolutionTracker:
    """Test suite for EvolutionTracker"""

    @pytest.fixture
    def tracker(self, temp_data_dir):
        """Create an EvolutionTracker instance with temp directory"""
        # EvolutionTracker doesn't take storage_dir, it uses a fixed path
        tracker = EvolutionTracker()
        # Override the storage path for testing
        tracker.evolution_file = temp_data_dir / "evolution_history.json"
        tracker.evolution_file.parent.mkdir(parents=True, exist_ok=True)
        return tracker

    def test_initialization(self, tracker, temp_data_dir):
        """Test tracker initialization"""
        assert tracker.evolution_file == temp_data_dir / "evolution_history.json"
        assert tracker.evolution_file.parent.exists()

    def test_add_evolution(self, tracker):
        """Test adding a new evolution"""
        # Start with clean history
        tracker.history = {"evolutions": [], "fingerprints": set()}
        tracker._save_history()

        evolution = {
            "type": "feature",
            "feature": "testing_framework",
            "description": "Add comprehensive testing",
            "debate_id": "test_debate_123",
        }

        result = tracker.add_evolution(evolution)
        assert result is True

        # Verify evolution was saved
        history = tracker._load_history()
        assert len(history["evolutions"]) == 1
        assert history["evolutions"][0]["feature"] == "testing_framework"

    def test_duplicate_evolution_detection(self, tracker):
        """Test that duplicate evolutions are detected"""
        # Start with clean history
        tracker.history = {"evolutions": [], "fingerprints": set()}
        tracker._save_history()

        evolution = {
            "type": "feature",
            "feature": "testing_framework",
            "description": "Add testing",
            "debate_id": "test_debate_123",
        }

        # Add first time
        assert tracker.add_evolution(evolution) is True

        # Try to add duplicate
        assert tracker.add_evolution(evolution) is False

    def test_get_evolution_summary(self, tracker):
        """Test getting evolution summary"""
        # Start with clean history
        tracker.history = {"evolutions": [], "fingerprints": set()}
        tracker._save_history()

        # Add some evolutions
        evolutions = [
            {"type": "feature", "feature": "test1", "description": "Test 1"},
            {"type": "feature", "feature": "test2", "description": "Test 2"},
            {"type": "enhancement", "feature": "test3", "description": "Test 3"},
            {"type": "bugfix", "feature": "test4", "description": "Test 4"},
        ]

        for evo in evolutions:
            tracker.add_evolution(evo)

        summary = tracker.get_evolution_summary()
        assert summary["total_evolutions"] == 4
        assert summary["evolution_types"]["feature"] == 2
        assert summary["evolution_types"]["enhancement"] == 1
        assert summary["evolution_types"]["bugfix"] == 1

    def test_get_recent_evolutions(self, tracker):
        """Test getting recent evolutions"""
        # Start with clean history
        tracker.history = {"evolutions": [], "fingerprints": set()}
        tracker._save_history()

        # Add some evolutions
        for i in range(10):
            evolution = {"type": "feature", "feature": f"test_{i}", "description": f"Test evolution {i}"}
            tracker.add_evolution(evolution)

        recent = tracker.get_recent_evolutions(5)
        assert len(recent) == 5
        # Most recent should be last in the list (chronological order)
        assert recent[-1]["feature"] == "test_9"
        assert recent[0]["feature"] == "test_5"

    def test_fingerprint_generation(self, tracker):
        """Test evolution fingerprint generation"""
        evolution1 = {"type": "feature", "feature": "testing", "description": "Add testing"}
        evolution2 = {"type": "feature", "feature": "testing", "description": "Add testing"}
        evolution3 = {"type": "feature", "feature": "monitoring", "description": "Add monitoring"}

        fp1 = tracker._generate_fingerprint(evolution1)
        fp2 = tracker._generate_fingerprint(evolution2)
        fp3 = tracker._generate_fingerprint(evolution3)

        assert fp1 == fp2  # Same content = same fingerprint
        assert fp1 != fp3  # Different content = different fingerprint

    def test_persistence(self, tracker):
        """Test that evolutions persist across tracker instances"""
        # Start with clean history
        tracker.history = {"evolutions": [], "fingerprints": set()}
        tracker._save_history()

        evolution = {"type": "feature", "feature": "persistence_test", "description": "Test persistence"}

        tracker.add_evolution(evolution)

        # Create new tracker instance
        new_tracker = EvolutionTracker()
        new_tracker.evolution_file = tracker.evolution_file
        summary = new_tracker.get_evolution_summary()

        assert summary["total_evolutions"] == 1
        recent = new_tracker.get_recent_evolutions(1)
        assert recent[0]["feature"] == "persistence_test"
