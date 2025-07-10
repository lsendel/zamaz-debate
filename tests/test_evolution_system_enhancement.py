#!/usr/bin/env python3
"""
Tests for the enhanced Evolution System Intelligence
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.core.evolution_tracker import EvolutionTracker


class TestEvolutionSystemEnhancement:
    """Test suite for the enhanced evolution system"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = EvolutionTracker(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_enhanced_feature_extraction(self):
        """Test advanced feature extraction capabilities"""
        # Test evolution system enhancement detection
        claude_response = "We need to fix the evolution system that's stuck in a loop"
        gemini_response = "The evolution tracking system requires a meta-level audit"
        
        feature = self.tracker._extract_feature(claude_response, gemini_response)
        assert feature == "evolution_system_enhancement"
        
        # Test testing framework detection
        claude_response = "Implement comprehensive unit testing framework"
        gemini_response = "Add integration tests and test coverage"
        
        feature = self.tracker._extract_feature(claude_response, gemini_response)
        assert feature == "testing_framework"
        
        # Test security enhancement detection
        claude_response = "We need security hardening for the API"
        gemini_response = "Add authentication and vulnerability scanning"
        
        feature = self.tracker._extract_feature(claude_response, gemini_response)
        assert feature == "security_enhancement"
        
        # Test fallback to unique hash for unrecognized patterns
        claude_response = "This is completely novel functionality"
        gemini_response = "Never seen before approach"
        
        feature = self.tracker._extract_feature(claude_response, gemini_response)
        assert feature.startswith("custom_improvement_")
    
    def test_semantic_similarity_detection(self):
        """Test enhanced duplicate detection with semantic similarity"""
        # Add first evolution
        evolution1 = {
            "type": "feature",
            "feature": "performance_optimization",
            "description": "Optimize system performance with caching and profiling"
        }
        
        assert self.tracker.add_evolution(evolution1) == True
        
        # Try to add similar evolution (should be detected as duplicate)
        evolution2 = {
            "type": "feature", 
            "feature": "performance_profiling",
            "description": "Add performance monitoring and optimization tools"
        }
        
        assert self.tracker.add_evolution(evolution2) == False
        
        # Add different evolution (should be accepted)
        evolution3 = {
            "type": "security",
            "feature": "security_enhancement",
            "description": "Implement comprehensive security measures"
        }
        
        assert self.tracker.add_evolution(evolution3) == True
    
    def test_evolution_validation(self):
        """Test evolution validation logic"""
        # Valid evolution
        valid_evolution = {
            "type": "feature",
            "feature": "test_feature",
            "description": "This is a valid evolution description"
        }
        
        assert self.tracker._validate_evolution(valid_evolution) == True
        
        # Invalid evolution - missing required field
        invalid_evolution1 = {
            "type": "feature",
            "feature": "test_feature"
            # Missing description
        }
        
        assert self.tracker._validate_evolution(invalid_evolution1) == False
        
        # Invalid evolution - invalid type
        invalid_evolution2 = {
            "type": "invalid_type",
            "feature": "test_feature",
            "description": "This has invalid type"
        }
        
        assert self.tracker._validate_evolution(invalid_evolution2) == False
        
        # Invalid evolution - description too short
        invalid_evolution3 = {
            "type": "feature",
            "feature": "test_feature",
            "description": "Short"
        }
        
        assert self.tracker._validate_evolution(invalid_evolution3) == False
    
    def test_impact_score_calculation(self):
        """Test impact score calculation"""
        # High impact evolution (security)
        security_evolution = {
            "type": "security",
            "feature": "security_enhancement",
            "description": "Critical security hardening with authentication and encryption",
            "priority": "high"
        }
        
        score = self.tracker._calculate_impact_score(security_evolution)
        assert score >= 10.0  # Should be high impact
        
        # Medium impact evolution (feature)
        feature_evolution = {
            "type": "feature",
            "feature": "ui_enhancement",
            "description": "Simple UI improvement",
            "priority": "medium"
        }
        
        score = self.tracker._calculate_impact_score(feature_evolution)
        assert 3.0 <= score <= 8.0  # Should be medium impact
        
        # Low impact evolution (documentation)
        doc_evolution = {
            "type": "documentation",
            "feature": "documentation",
            "description": "Update README file",
            "priority": "low"
        }
        
        score = self.tracker._calculate_impact_score(doc_evolution)
        assert score <= 5.0  # Should be lower impact
    
    def test_diversity_score_calculation(self):
        """Test diversity score calculation"""
        # High diversity case
        type_counts = {"feature": 2, "security": 2, "testing": 2, "fix": 1}
        feature_counts = {"feat1": 1, "feat2": 1, "feat3": 1, "feat4": 1}
        total = 7
        
        diversity = self.tracker._calculate_diversity_score(type_counts, feature_counts, total)
        assert diversity > 0.5  # Should be reasonably diverse
        
        # Low diversity case (all same type)
        type_counts = {"feature": 10}
        feature_counts = {"same_feature": 10}
        total = 10
        
        diversity = self.tracker._calculate_diversity_score(type_counts, feature_counts, total)
        assert diversity < 0.3  # Should be low diversity
    
    def test_evolution_recommendations(self):
        """Test evolution recommendation system"""
        # Add many feature evolutions to create imbalance
        for i in range(8):
            evolution = {
                "type": "feature",
                "feature": f"feature_{i}",
                "description": f"Feature {i} description for testing"
            }
            self.tracker.add_evolution(evolution)
        
        recommendations = self.tracker.get_evolution_recommendations()
        
        # Should recommend adding missing types
        missing_types = [r for r in recommendations if r["type"] == "missing_evolution_type"]
        assert len(missing_types) > 0
        
        # Should recommend reducing imbalance
        imbalance_recs = [r for r in recommendations if r["type"] == "imbalanced_evolution_types"]
        assert len(imbalance_recs) > 0
    
    def test_rollback_functionality(self):
        """Test evolution rollback capability"""
        # Add evolution
        evolution = {
            "type": "feature",
            "feature": "test_feature",
            "description": "Test evolution for rollback"
        }
        
        assert self.tracker.add_evolution(evolution) == True
        
        # Get the evolution ID
        evolutions = self.tracker.get_recent_evolutions(1)
        evolution_id = evolutions[0]["id"]
        
        # Rollback the evolution
        assert self.tracker.rollback_evolution(evolution_id) == True
        
        # Check that active evolutions doesn't include rolled back one
        active_evolutions = self.tracker.get_active_evolutions()
        active_ids = [evo["id"] for evo in active_evolutions]
        assert evolution_id not in active_ids
    
    def test_comprehensive_summary(self):
        """Test comprehensive evolution summary"""
        # Add diverse evolutions
        evolutions = [
            {"type": "feature", "feature": "feat1", "description": "Feature 1"},
            {"type": "security", "feature": "sec1", "description": "Security 1"}, 
            {"type": "testing", "feature": "test1", "description": "Testing 1"},
            {"type": "fix", "feature": "fix1", "description": "Bug fix 1"}
        ]
        
        for evo in evolutions:
            self.tracker.add_evolution(evo)
        
        summary = self.tracker.get_evolution_summary()
        
        # Check summary completeness
        assert "total_evolutions" in summary
        assert "evolution_types" in summary
        assert "diversity_score" in summary
        assert "avg_impact_score" in summary
        assert "high_impact_evolutions" in summary
        assert "duplicate_prevention_active" in summary
        
        # Check type distribution
        assert summary["evolution_types"]["feature"] == 1
        assert summary["evolution_types"]["security"] == 1
        assert summary["evolution_types"]["testing"] == 1
        assert summary["evolution_types"]["fix"] == 1
        
        # Check diversity score is reasonable
        assert summary["diversity_score"] > 0.3
    
    def test_feature_similarity_groups(self):
        """Test feature similarity group detection"""
        # Test performance group
        assert self.tracker._are_features_similar("performance_optimization", "performance_profiling") == True
        
        # Test testing group
        assert self.tracker._are_features_similar("testing_framework", "automated_testing") == True
        
        # Test security group
        assert self.tracker._are_features_similar("security_enhancement", "security_hardening") == True
        
        # Test different groups
        assert self.tracker._are_features_similar("performance_optimization", "security_enhancement") == False
    
    def test_description_similarity(self):
        """Test description similarity detection"""
        desc1 = "implement comprehensive testing framework with unit tests"
        desc2 = "add comprehensive testing framework and unit testing"
        
        # Should be similar (high word overlap)
        assert self.tracker._are_descriptions_similar(desc1, desc2) == True
        
        desc3 = "implement user interface improvements"
        desc4 = "add comprehensive testing framework"
        
        # Should not be similar (low word overlap)
        assert self.tracker._are_descriptions_similar(desc3, desc4) == False


if __name__ == "__main__":
    pytest.main([__file__])